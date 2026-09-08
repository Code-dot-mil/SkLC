import hashlib
import json
import os
import tarfile
from pathlib import Path

import pytest
import yaml
from skill_exchange.release import ReleaseError, build_release, extract_release_notes, validate_version

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
    prebuilt = repo / "products" / "deployment-kit" / "prebuilt"
    _write(prebuilt / "README.md")
    docs = prebuilt / "docs"
    for name in ("install.md", "deploy-gitlab-pages.md", "deploy-static-hosting.md"):
        _write(docs / name)
    _write(prebuilt / ".gitlab-ci.yml")
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
            repo / "products" / "skill-catalog" / "skills" / "ai4sdlc" / skill / "SKILL.md",
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
    _write(repo / "contracts" / "release-manifest" / "v1" / "example.json", "{}\n")
    _write(repo / "contracts" / "skill-package" / "v1" / "skill.schema.json", "{}\n")

    site = repo / "products" / "deployment-kit" / "site" / "dist"
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
        for relative, digest in checksums.items():
            content = archive.extractfile(f"{root}/{relative}").read()
            assert hashlib.sha256(content).hexdigest() == digest
    return root, files, manifest, checksums


def _build_delivered_deployment_package(tmp_path: Path) -> Path:
    repo, site = _release_fixture(tmp_path)
    repository_root = Path(__file__).parents[1]
    delivered_prebuilt = repository_root / "products" / "deployment-kit" / "prebuilt"
    fixture_prebuilt = repo / "products" / "deployment-kit" / "prebuilt"
    (fixture_prebuilt / ".gitlab-ci.yml").write_bytes((delivered_prebuilt / ".gitlab-ci.yml").read_bytes())
    (fixture_prebuilt / "docs" / "install.md").write_bytes((delivered_prebuilt / "docs" / "install.md").read_bytes())
    delivered_schema = repository_root / "contracts" / "release-manifest" / "v1" / "release-manifest.schema.json"
    fixture_schema = repo / "contracts" / "release-manifest" / "v1" / "release-manifest.schema.json"
    fixture_schema.write_bytes(delivered_schema.read_bytes())
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
    return extracted / "deployment-kit-prebuilt-1.2.3"


def _run_delivered_gitlab_verification(monkeypatch, package_root: Path) -> None:
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


def _run_delivered_install_verification(monkeypatch, package_root: Path) -> None:
    documentation = (package_root / "docs" / "install.md").read_text()
    lines = documentation.splitlines()
    start = lines.index("python3 - <<'PY'") + 1
    end = lines.index("PY", start)
    python_source = "\n".join(lines[start:end])

    previous = Path.cwd()
    monkeypatch.chdir(package_root)
    try:
        exec(compile(python_source, "docs/install.md", "exec"), {})
    finally:
        os.chdir(previous)


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
    assert external["produces"] == {"release_manifest": ["skill-exchange-release-manifest/v1"]}
    assert external["consumes"] == {}
    assert [entry["path"] for entry in external["artifacts"]] == [
        "deployment-kit-prebuilt-1.2.3.tar.gz",
        "skill-catalog-1.2.3.tar.gz",
    ]
    checksums = {
        path: digest
        for line in (output / "SHA256SUMS.txt").read_text().splitlines()
        for digest, path in [line.split("  ", 1)]
    }
    assert list(checksums) == [
        "deployment-kit-prebuilt-1.2.3.tar.gz",
        "skill-catalog-1.2.3.tar.gz",
        "release-manifest.json",
    ]
    for relative, digest in checksums.items():
        assert hashlib.sha256((output / relative).read_bytes()).hexdigest() == digest
    assert {entry["path"]: entry["sha256"].removeprefix("sha256:") for entry in external["artifacts"]} == {
        path: digest for path, digest in checksums.items() if path != "release-manifest.json"
    }


def test_build_release_is_reproducible_for_a_fixed_revision_and_timestamp(tmp_path: Path):
    repo, site = _release_fixture(tmp_path)
    first = tmp_path / "first"
    second = tmp_path / "second"

    for output in (first, second):
        build_release(
            repo_root=repo,
            site_dir=site,
            output_dir=output,
            version="1.2.3",
            source_revision="abc123",
            source_date_epoch=1_800_000_000,
        )

    assert {path.name: path.read_bytes() for path in first.iterdir()} == {
        path.name: path.read_bytes() for path in second.iterdir()
    }


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
    assert manifest["produces"] == {"release_manifest": ["skill-exchange-release-manifest/v1"]}
    assert manifest["consumes"] == {}
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
    assert "contracts/skill-package/v1/skill.schema.json" in files
    assert "catalog-policy.yaml" not in files
    assert not any(path.startswith("site/") or path.startswith(".github/") for path in files)
    assert manifest["product"] == "skill-catalog"
    assert manifest["produces"] == {}
    assert manifest["consumes"] == {
        "skill_package": ["skill-exchange-skill-package/v1"],
        "release_manifest": ["skill-exchange-release-manifest/v1"],
    }
    assert {entry["path"]: entry["sha256"].removeprefix("sha256:") for entry in manifest["artifacts"]} == checksums


@pytest.mark.parametrize("version", ["01.2.3", "1.02.3", "1.2.03", "1.2.3-01", "1.2.3-", "1.2.3+"])
def test_validate_version_rejects_invalid_semver(version: str):
    with pytest.raises(ReleaseError, match="SemVer"):
        validate_version(version)


@pytest.mark.parametrize("version", ["0.0.0", "1.2.3", "1.2.3-alpha.1", "1.2.3+build.7"])
def test_validate_version_accepts_semver(version: str):
    validate_version(version)


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


def test_build_release_accepts_download_queries_and_fragments(tmp_path: Path):
    repo, site = _release_fixture(tmp_path)
    (site / "index.html").write_text('<a href="downloads/example.zip?download=1#skill">Download</a>\n')
    _write(site / "catalog.json", '{"download":"downloads/example.zip#skill"}\n')
    _write(site / "catalog.js", 'const download = "downloads/example.zip?download=1";\n')

    build_release(
        repo_root=repo,
        site_dir=site,
        output_dir=tmp_path / "release",
        version="1.2.3",
        source_revision="abc123",
        source_date_epoch=1_800_000_000,
    )


@pytest.mark.parametrize(
    ("source_name", "source_text"),
    [
        ("index.html", '<a href="downloads/missing.zip?download=1">Download</a>\n'),
        ("catalog.json", '{"download":"downloads/missing.zip#skill"}\n'),
        ("catalog.js", 'const download = "downloads/missing.zip?download=1#skill";\n'),
    ],
)
def test_build_release_checks_download_references_before_queries_and_fragments(
    tmp_path: Path, source_name: str, source_text: str
):
    repo, site = _release_fixture(tmp_path)
    _write(site / source_name, source_text)

    with pytest.raises(ReleaseError, match="missing or unsafe download: downloads/missing.zip"):
        build_release(
            repo_root=repo,
            site_dir=site,
            output_dir=tmp_path / "release",
            version="1.2.3",
            source_revision="abc123",
            source_date_epoch=1_800_000_000,
        )


def test_build_release_rejects_parent_download_path_component(tmp_path: Path):
    repo, site = _release_fixture(tmp_path)
    (site / "index.html").write_text('<a href="downloads/sub/../example.zip">Download</a>\n')

    with pytest.raises(ReleaseError, match=r"missing or unsafe download: downloads/sub/\.\./example\.zip"):
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
    package_root = _build_delivered_deployment_package(tmp_path)
    _run_delivered_gitlab_verification(monkeypatch, package_root)


def test_delivered_gitlab_verification_rejects_changed_site_file(monkeypatch, tmp_path: Path):
    package_root = _build_delivered_deployment_package(tmp_path)
    (package_root / "public" / "assets" / "site.css").write_text("changed\n")

    with pytest.raises(SystemExit, match="checksum mismatch: public/assets/site.css"):
        _run_delivered_gitlab_verification(monkeypatch, package_root)


def test_delivered_gitlab_verification_rejects_wrong_product(monkeypatch, tmp_path: Path):
    package_root = _build_delivered_deployment_package(tmp_path)
    manifest_path = package_root / "release-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["product"] = "skill-catalog"
    manifest_path.write_text(json.dumps(manifest))

    with pytest.raises(SystemExit, match="not for deployment-kit-prebuilt"):
        _run_delivered_gitlab_verification(monkeypatch, package_root)


def test_delivered_install_verification_accepts_built_package(monkeypatch, tmp_path: Path):
    package_root = _build_delivered_deployment_package(tmp_path)

    _run_delivered_install_verification(monkeypatch, package_root)


def test_delivered_install_verification_rejects_schema_violation(monkeypatch, tmp_path: Path):
    package_root = _build_delivered_deployment_package(tmp_path)
    manifest_path = package_root / "release-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["source_revision"] = ""
    manifest_path.write_text(json.dumps(manifest))

    with pytest.raises(SystemExit, match=r"\$\.source_revision is too short"):
        _run_delivered_install_verification(monkeypatch, package_root)
