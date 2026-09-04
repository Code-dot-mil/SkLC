import json
import os
import tarfile
from pathlib import Path

import pytest
import yaml
from skill_exchange.release import ReleaseError, build_release, extract_release_notes

SKILLS = (
    "python-secure-code-review",
    "unit-test-generation",
    "inline-documentation",
    "code-change-description",
)


def _write(path: Path, content: str = "fixture\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _release_fixture(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    docs = repo / "products" / "deployment-kit" / "docs" / "prebuilt"
    for name in ("README.md", "install.md", "deploy-gitlab-pages.md", "deploy-static-hosting.md"):
        _write(docs / name)
    _write(repo / "products" / "deployment-kit" / "ci" / "gitlab" / "prebuilt" / ".gitlab-ci.yml")
    _write(repo / "products" / "skill-catalog" / "README.md")
    _write(
        repo / "products" / "skill-catalog" / "catalog-policy.yaml",
        yaml.safe_dump(
            {
                "schema_version": "skill-exchange-catalog-policy/v1",
                "mode": "include-list",
                "skills": list(SKILLS),
            },
            sort_keys=False,
        ),
    )
    for skill in SKILLS:
        _write(
            repo / "skills" / "ai4sdlc" / skill / "SKILL.md",
            f"---\nname: {skill}\ndescription: Fixture skill.\n---\n\n# {skill}\n",
        )
    manifest_fields = [
        "schema_version",
        "product",
        "version",
        "source_revision",
        "created_at",
        "produces",
        "consumes",
        "artifacts",
    ]
    _write(
        repo / "contracts" / "release-manifest" / "v1" / "release-manifest.schema.json",
        json.dumps({"required": manifest_fields, "properties": dict.fromkeys(manifest_fields, {})}) + "\n",
    )
    _write(repo / "contracts" / "skill-package" / "v1" / "metadata.schema.json", "{}\n")

    site = repo / "site" / "dist"
    _write(site / "index.html", '<a href="downloads/example.zip">Download</a>\n')
    _write(site / "assets" / "site.css")
    _write(site / "downloads" / "example.zip")
    _write(site / ".gitkeep")
    return repo, site


def _archive_files(path: Path) -> tuple[str, set[str], dict, dict[str, str]]:
    with tarfile.open(path, "r:gz") as archive:
        root = archive.getnames()[0].split("/", 1)[0]
        files = {name.removeprefix(f"{root}/") for name in archive.getnames() if archive.getmember(name).isfile()}
        manifest = json.load(archive.extractfile(f"{root}/release-manifest.json"))
        checksums = {}
        for line in archive.extractfile(f"{root}/SHA256SUMS.txt").read().decode().splitlines():
            digest, relative = line.split("  ", 1)
            checksums[relative] = digest
    return root, files, manifest, checksums


def test_build_release_creates_both_product_archives_and_external_metadata(tmp_path: Path):
    repo, site = _release_fixture(tmp_path)
    output = tmp_path / "release"

    built = build_release(
        repo_root=repo,
        site_dir=site,
        output_dir=output,
        version="1.2.3",
        source_revision="abc123",
        source_date_epoch=1_800_000_000,
    )

    assert [path.name for path in built] == [
        "deployment-kit-prebuilt-1.2.3.tar.gz",
        "skill-catalog-1.2.3.tar.gz",
        "release-manifest.json",
        "SHA256SUMS.txt",
    ]
    external = json.loads((output / "release-manifest.json").read_text())
    assert external["product"] == "sklc"
    assert [entry["path"] for entry in external["artifacts"]] == [
        "deployment-kit-prebuilt-1.2.3.tar.gz",
        "skill-catalog-1.2.3.tar.gz",
    ]
    checksum_paths = [line.split("  ", 1)[1] for line in (output / "SHA256SUMS.txt").read_text().splitlines()]
    assert checksum_paths == [
        "deployment-kit-prebuilt-1.2.3.tar.gz",
        "skill-catalog-1.2.3.tar.gz",
        "release-manifest.json",
    ]


def test_deployment_archive_has_release_layout_and_matching_integrity_files(tmp_path: Path):
    repo, site = _release_fixture(tmp_path)
    output = tmp_path / "release"
    build_release(
        repo_root=repo,
        site_dir=site,
        output_dir=output,
        version="1.2.3",
        source_revision="abc123",
        source_date_epoch=1_800_000_000,
    )

    root, files, manifest, checksums = _archive_files(output / "deployment-kit-prebuilt-1.2.3.tar.gz")

    assert root == "deployment-kit-prebuilt-1.2.3"
    assert {
        ".gitlab-ci.yml",
        "README.md",
        "docs/install.md",
        "docs/deploy-gitlab-pages.md",
        "docs/deploy-static-hosting.md",
        "contracts/release-manifest/v1/release-manifest.schema.json",
        "public/index.html",
        "public/assets/site.css",
        "public/downloads/example.zip",
        "release-manifest.json",
        "SHA256SUMS.txt",
    } == files
    assert "public/.gitkeep" not in files
    assert manifest["product"] == "deployment-kit-prebuilt"
    assert {entry["path"]: entry["sha256"].removeprefix("sha256:") for entry in manifest["artifacts"]} == checksums


def test_skill_catalog_archive_contains_only_policy_selected_skills(tmp_path: Path):
    repo, site = _release_fixture(tmp_path)
    output = tmp_path / "release"
    build_release(
        repo_root=repo,
        site_dir=site,
        output_dir=output,
        version="1.2.3",
        source_revision="abc123",
        source_date_epoch=1_800_000_000,
    )

    root, files, manifest, checksums = _archive_files(output / "skill-catalog-1.2.3.tar.gz")

    assert root == "skill-catalog-1.2.3"
    assert {path.split("/")[1] for path in files if path.startswith("skills/")} == set(SKILLS)
    assert "catalog-policy.yaml" not in files
    assert not any(path.startswith("site/") or path.startswith(".github/") for path in files)
    assert manifest["product"] == "skill-catalog"
    assert {entry["path"]: entry["sha256"].removeprefix("sha256:") for entry in manifest["artifacts"]} == checksums


def test_build_release_rejects_unknown_catalog_skill(tmp_path: Path):
    repo, site = _release_fixture(tmp_path)
    policy = repo / "products" / "skill-catalog" / "catalog-policy.yaml"
    content = yaml.safe_load(policy.read_text())
    content["skills"].append("missing-skill")
    policy.write_text(yaml.safe_dump(content), encoding="utf-8")

    with pytest.raises(ReleaseError, match="unknown skills: missing-skill"):
        build_release(
            repo_root=repo,
            site_dir=site,
            output_dir=tmp_path / "release",
            version="1.2.3",
            source_revision="abc123",
            source_date_epoch=1_800_000_000,
        )


def test_build_release_rejects_missing_site_download(tmp_path: Path):
    repo, site = _release_fixture(tmp_path)
    (site / "downloads" / "example.zip").unlink()

    with pytest.raises(ReleaseError, match="missing or unsafe download: downloads/example.zip"):
        build_release(
            repo_root=repo,
            site_dir=site,
            output_dir=tmp_path / "release",
            version="1.2.3",
            source_revision="abc123",
            source_date_epoch=1_800_000_000,
        )


def test_build_release_rejects_root_absolute_download_reference(tmp_path: Path):
    repo, site = _release_fixture(tmp_path)
    (site / "index.html").write_text('<a href="/downloads/example.zip">Download</a>\n')

    with pytest.raises(ReleaseError, match="site download references must be relative: index.html"):
        build_release(
            repo_root=repo,
            site_dir=site,
            output_dir=tmp_path / "release",
            version="1.2.3",
            source_revision="abc123",
            source_date_epoch=1_800_000_000,
        )


def test_extract_release_notes_returns_only_requested_version(tmp_path: Path):
    notes = tmp_path / "RELEASE_NOTES.md"
    notes.write_text("# Release Notes\n\n## 1.2.3\n\n- Current change.\n\n## 1.2.2\n\n- Older change.\n")

    assert extract_release_notes(notes, "1.2.3") == "## 1.2.3\n\n- Current change.\n"


def test_delivered_gitlab_verification_accepts_built_package(monkeypatch, tmp_path: Path):
    repo, site = _release_fixture(tmp_path)
    repository_root = Path(__file__).parents[1]
    delivered_ci = repository_root / "products" / "deployment-kit" / "ci" / "gitlab" / "prebuilt" / ".gitlab-ci.yml"
    (repo / "products" / "deployment-kit" / "ci" / "gitlab" / "prebuilt" / ".gitlab-ci.yml").write_bytes(
        delivered_ci.read_bytes()
    )
    output = tmp_path / "release"
    build_release(
        repo_root=repo,
        site_dir=site,
        output_dir=output,
        version="1.2.3",
        source_revision="abc123",
        source_date_epoch=1_800_000_000,
    )
    extracted = tmp_path / "extracted"
    with tarfile.open(output / "deployment-kit-prebuilt-1.2.3.tar.gz", "r:gz") as archive:
        archive.extractall(extracted, filter="data")
    package_root = extracted / "deployment-kit-prebuilt-1.2.3"
    definition = yaml.safe_load((package_root / ".gitlab-ci.yml").read_text())
    verification = next(command for command in definition["pages"]["script"] if "python3 - <<'PY'" in command)
    lines = verification.splitlines()
    python_source = "\n".join(lines[1:-1])

    previous = Path.cwd()
    monkeypatch.chdir(package_root)
    try:
        exec(compile(python_source, ".gitlab-ci.yml", "exec"), {})
    finally:
        os.chdir(previous)
