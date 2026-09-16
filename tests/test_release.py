import hashlib
import io
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path
from zipfile import ZipFile

import pytest
import yaml
from skill_exchange.release import (
    ReleaseError,
    _regular_files,
    build_release,
    copy_release_file,
    copy_release_tree,
    extract_release_notes,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_SCHEMA_PATH = Path("contracts/release-manifest/v1/release-manifest.schema.json")
VERSION = "1.2.3"
SOURCE_REVISION = "a" * 40


def _write(path: Path, content: bytes = b"release input\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


@pytest.fixture
def make_link():
    links: list[Path] = []

    def create(link: Path, target: Path, *, kind: str = "symlink", directory: bool = True) -> None:
        if kind == "junction":
            if os.name != "nt":
                pytest.skip("directory junctions are Windows-only")
            subprocess.run(
                [
                    "powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
                    "$ErrorActionPreference = 'Stop'\n"
                    "New-Item -ItemType Junction -Path $env:SKLC_TEST_LINK -Target $env:SKLC_TEST_TARGET | Out-Null",
                ],
                env={**os.environ, "SKLC_TEST_LINK": str(link), "SKLC_TEST_TARGET": str(target)},
                check=True,
                capture_output=True,
                text=True,
            )
        else:
            try:
                link.symlink_to(target, target_is_directory=directory)
            except OSError as error:
                if os.name == "nt" and error.winerror == 1314:
                    pytest.skip("Windows does not grant symbolic-link creation privilege")
                raise
        links.append(link)

    yield create

    # Remove only each link itself, never the linked directory or its contents.
    for link in reversed(links):
        if link.is_junction():
            link.rmdir()
        else:
            link.unlink(missing_ok=True)


def testcopy_release_tree_preserves_regular_files_and_empty_directories(tmp_path: Path):
    source = tmp_path / "site"
    expected = {"index.html": b"<html></html>\n", "downloads/skill.zip": b"\x00\xff", ".hidden": b"hidden"}
    for name, content in expected.items():
        _write(source / name, content)
    (source / "assets" / "empty").mkdir(parents=True)
    destination = tmp_path / "package" / "public"

    copy_release_tree(source, destination)

    actual = {path.relative_to(destination).as_posix(): path.read_bytes() for path in _regular_files(destination)}
    assert actual == expected
    assert (destination / "assets" / "empty").is_dir()


@pytest.mark.parametrize("kind", ["symlink", "junction"])
@pytest.mark.parametrize("placement", ["root", "nested", "ancestor"])
def testcopy_release_tree_rejects_directory_links_before_copying(tmp_path: Path, make_link, kind: str, placement: str):
    outside = tmp_path / "outside"
    _write(outside / "site" / "index.html", b"outside site\n")
    _write(outside / "site" / "private.txt", b"must not be packaged\n")
    source = tmp_path / "input"
    if placement == "root":
        make_link(source, outside / "site", kind=kind)
    elif placement == "ancestor":
        make_link(source, outside, kind=kind)
        source = source / "site"
    else:
        _write(source / "index.html", b"intended site\n")
        make_link(source / "linked", outside / "site", kind=kind)
    destination = tmp_path / "package" / "public"

    with pytest.raises(ReleaseError, match="link"):
        copy_release_tree(source, destination)

    assert not destination.exists()
    assert (outside / "site" / "private.txt").read_bytes() == b"must not be packaged\n"
    with pytest.raises(ReleaseError, match="link"):
        _regular_files(source)


@pytest.mark.parametrize("broken", [False, True])
def testcopy_release_tree_rejects_file_links_before_copying(tmp_path: Path, make_link, broken: bool):
    source = tmp_path / "site"
    _write(source / "index.html")
    outside = tmp_path / "outside.txt"
    if not broken:
        _write(outside, b"must not be packaged\n")
    make_link(source / "linked.txt", outside, directory=False)
    destination = tmp_path / "package" / "public"

    with pytest.raises(ReleaseError, match="link"):
        copy_release_tree(source, destination)

    assert not destination.exists()


@pytest.mark.parametrize("kind", ["symlink", "junction"])
def testcopy_release_file_rejects_linked_parent(tmp_path: Path, make_link, kind: str):
    outside = tmp_path / "outside"
    _write(outside / "install.md", b"outside file\n")
    linked = tmp_path / "linked"
    make_link(linked, outside, kind=kind)
    destination = tmp_path / "package" / "docs" / "install.md"

    with pytest.raises(ReleaseError, match="link"):
        copy_release_file(linked / "install.md", destination)

    assert not destination.parent.exists()


def testcopy_release_file_preserves_regular_file(tmp_path: Path):
    source = tmp_path / "install.md"
    _write(source, b"installation instructions\n")
    destination = tmp_path / "package" / "docs" / "install.md"

    copy_release_file(source, destination)

    assert destination.read_bytes() == source.read_bytes()


@pytest.mark.parametrize("broken", [False, True])
def testcopy_release_file_rejects_symbolic_link(tmp_path: Path, make_link, broken: bool):
    outside = tmp_path / "outside.md"
    if not broken:
        _write(outside)
    source = tmp_path / "install.md"
    make_link(source, outside, directory=False)
    destination = tmp_path / "package" / "docs" / "install.md"

    with pytest.raises(ReleaseError, match="link"):
        copy_release_file(source, destination)

    assert not destination.parent.exists()


def testcopy_release_tree_rejects_broken_source_link(tmp_path: Path, make_link):
    source = tmp_path / "site"
    make_link(source, tmp_path / "missing")
    destination = tmp_path / "package" / "public"

    with pytest.raises(ReleaseError, match="link"):
        copy_release_tree(source, destination)

    assert not destination.parent.exists()


@pytest.mark.parametrize("copy", [copy_release_file, copy_release_tree])
def test_copy_rejects_missing_source(tmp_path: Path, copy):
    destination = tmp_path / "package" / "missing"

    with pytest.raises(ReleaseError, match="missing"):
        copy(tmp_path / "missing", destination)

    assert not destination.parent.exists()


def _release_fixture(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    product = repo / "products" / "deployment-kit"
    for name in ("README.md", "install.md", "deploy-gitlab-pages.md", "deploy-static-hosting.md"):
        _write(product / "docs" / "prebuilt" / name,
               (REPOSITORY_ROOT / "products/deployment-kit/docs/prebuilt" / name).read_bytes())
    _write(product / "ci/gitlab/prebuilt/.gitlab-ci.yml",
           (REPOSITORY_ROOT / "products/deployment-kit/ci/gitlab/prebuilt/.gitlab-ci.yml").read_bytes())
    _write(product / "scripts/verify_prebuilt.py",
           (REPOSITORY_ROOT / "products/deployment-kit/scripts/verify_prebuilt.py").read_bytes())
    _write(repo / MANIFEST_SCHEMA_PATH, (REPOSITORY_ROOT / MANIFEST_SCHEMA_PATH).read_bytes())

    site = repo / "site" / "dist"
    _write(site / "index.html", b'<a href="downloads/example.zip">Download</a>\n')
    _write(site / "assets" / "site.css", b"body { color: black; }\n")
    (site / "assets" / "empty").mkdir()
    # These names are ordinary nested assets, not the package's root metadata.
    _write(site / "assets" / "release-manifest.json", b"{}\n")
    _write(site / "assets" / "SHA256SUMS.txt", b"nested asset\n")
    _write(site / "skills" / "example" / "index.html", b"<h1>Example skill</h1>\n")
    zip_bytes = io.BytesIO()
    with ZipFile(zip_bytes, "w") as archive:
        archive.writestr("example/SKILL.md", "---\nname: example\ndescription: Example skill.\n---\n# Example\n")
    _write(site / "downloads" / "example.zip", zip_bytes.getvalue())
    _write(site / ".gitkeep", b"")
    return repo, site


def _build(repo: Path, site: Path, output: Path, *, version: str = VERSION) -> list[Path]:
    return build_release(
        repo_root=repo,
        site_dir=site,
        output_dir=output,
        version=version,
        source_revision=SOURCE_REVISION,
        source_date_epoch=0,
    )


def _checksums(path: Path) -> dict[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    entries = [line.split("  ", 1) for line in lines]
    assert len({name for _, name in entries}) == len(entries)
    return {name: digest for digest, name in entries}


def test_build_release_extracts_prebuilt_only_package_with_matching_checksums(tmp_path: Path):
    repo, site = _release_fixture(tmp_path)
    # Unrelated repository files must not be swept into the customer archive.
    _write(repo / "skills" / "unpublished" / "SKILL.md", b"not released\n")
    _write(repo / ".exchange" / "private.txt", b"not released\n")
    output = tmp_path / "release"

    built = _build(repo, site, output)

    archive_name = f"deployment-kit-prebuilt-{VERSION}.tar.gz"
    manifest_name = f"deployment-kit-prebuilt-{VERSION}.release-manifest.json"
    checksums_name = f"deployment-kit-prebuilt-{VERSION}.SHA256SUMS.txt"
    assert [path.name for path in built] == [archive_name, manifest_name, checksums_name]
    assert {path.name for path in output.iterdir()} == {path.name for path in built}
    extracted = tmp_path / "extracted"
    with tarfile.open(built[0], "r:gz") as archive:
        assert all(member.isfile() or member.isdir() for member in archive.getmembers())
        assert {member.name.split("/", 1)[0] for member in archive.getmembers()} == {
            f"deployment-kit-prebuilt-{VERSION}"
        }
        archive.extractall(extracted, filter="data")
    package = extracted / f"deployment-kit-prebuilt-{VERSION}"
    expected = {
        ".gitlab-ci.yml": repo / "products/deployment-kit/ci/gitlab/prebuilt/.gitlab-ci.yml",
        "README.md": repo / "products/deployment-kit/docs/prebuilt/README.md",
        MANIFEST_SCHEMA_PATH.as_posix(): repo / MANIFEST_SCHEMA_PATH,
        "scripts/verify_prebuilt.py": repo / "products/deployment-kit/scripts/verify_prebuilt.py",
    }
    expected.update({
        f"docs/{name}": repo / "products/deployment-kit/docs/prebuilt" / name
        for name in ("install.md", "deploy-gitlab-pages.md", "deploy-static-hosting.md")
    })
    expected.update({
        f"public/{path.relative_to(site).as_posix()}": path
        for path in site.rglob("*") if path.is_file() and path != site / ".gitkeep"
    })
    files = {path.relative_to(package).as_posix() for path in package.rglob("*") if path.is_file()}
    assert files == set(expected) | {"release-manifest.json", "SHA256SUMS.txt"}
    for relative, source in expected.items():
        assert (package / relative).read_bytes() == source.read_bytes()
    assert (package / "public/assets/empty").is_dir()

    digests = {relative: hashlib.sha256(source.read_bytes()).hexdigest() for relative, source in expected.items()}
    manifest = json.loads((package / "release-manifest.json").read_text(encoding="utf-8"))
    assert manifest == {
        "schema_version": "skill-exchange-release-manifest/v1",
        "product": "deployment-kit-prebuilt",
        "version": VERSION,
        "source_revision": SOURCE_REVISION,
        "created_at": "1970-01-01T00:00:00Z",
        "produces": {"release_manifest": ["skill-exchange-release-manifest/v1"]},
        "consumes": {},
        "artifacts": [{"path": relative, "sha256": f"sha256:{digests[relative]}"} for relative in sorted(expected)],
    }
    assert _checksums(package / "SHA256SUMS.txt") == digests
    assert built[1].read_bytes() == (package / "release-manifest.json").read_bytes()
    assert _checksums(built[2]) == {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in built[:2]
    }


@pytest.mark.parametrize("kind", ["symlink", "junction"])
@pytest.mark.parametrize("placement", ["site-root", "site-parent", "site-child", "repo-root"])
def test_build_release_rejects_linked_inputs_without_creating_artifacts(
    tmp_path: Path, make_link, kind: str, placement: str
):
    repo, site = _release_fixture(tmp_path)
    outside_repo, outside_site = _release_fixture(tmp_path / "outside")
    _write(outside_site / "private.txt", b"must not be packaged\n")
    linked = tmp_path / "linked"
    if placement == "site-root":
        make_link(linked, outside_site, kind=kind)
        site = linked
    elif placement == "site-parent":
        make_link(linked, outside_repo, kind=kind)
        site = linked / "site" / "dist"
    elif placement == "site-child":
        make_link(site / "linked", outside_site, kind=kind)
    else:
        make_link(linked, outside_repo, kind=kind)
        repo, site = linked, linked / "site" / "dist"
    output = tmp_path / "release"

    with pytest.raises(ReleaseError, match="link"):
        _build(repo, site, output)

    assert not output.exists()
    assert (outside_site / "private.txt").read_bytes() == b"must not be packaged\n"


def _run_build_cli(repo: Path, output: Path, *extra_args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable, "-m", "skill_exchange.release", "build", "--repo-root", str(repo),
            "--version", VERSION, "--source-revision", SOURCE_REVISION, "--output-dir", str(output), *extra_args,
        ],
        cwd=repo,
        env={**os.environ, "PYTHONPATH": str(REPOSITORY_ROOT / "scripts"), "SOURCE_DATE_EPOCH": "0"},
        capture_output=True,
        text=True,
        check=False,
    )


def test_build_cli_uses_existing_site_layout(tmp_path: Path):
    repo, _ = _release_fixture(tmp_path)
    output = tmp_path / "release"

    result = _run_build_cli(repo, output)

    assert result.returncode == 0, result.stderr
    assert [Path(path).name for path in json.loads(result.stdout)["artifacts"]] == [
        f"deployment-kit-prebuilt-{VERSION}.tar.gz",
        f"deployment-kit-prebuilt-{VERSION}.release-manifest.json",
        f"deployment-kit-prebuilt-{VERSION}.SHA256SUMS.txt",
    ]


@pytest.mark.parametrize("kind", ["symlink", "junction"])
@pytest.mark.parametrize("absolute", [False, True])
def test_build_cli_does_not_resolve_away_source_links(tmp_path: Path, make_link, kind: str, absolute: bool):
    repo, _ = _release_fixture(tmp_path)
    _, outside_site = _release_fixture(tmp_path / "outside")
    linked = repo / "linked-site"
    make_link(linked, outside_site, kind=kind)
    output = tmp_path / "release"

    result = _run_build_cli(repo, output, "--site-dir", str(linked) if absolute else "linked-site")

    assert result.returncode != 0
    assert "link" in result.stderr
    assert not output.exists()


@pytest.mark.parametrize("missing", ["index.html", "assets", "downloads"])
def test_build_release_requires_site_layout(tmp_path: Path, missing: str):
    repo, _ = _release_fixture(tmp_path)
    site = tmp_path / "incomplete-site"
    site.mkdir()
    for name in ("index.html", "assets", "downloads"):
        if name == missing:
            continue
        if name == "index.html":
            _write(site / name)
        else:
            (site / name).mkdir()
    output = tmp_path / "release"

    with pytest.raises(ReleaseError, match=f"public/{missing}"):
        _build(repo, site, output)

    assert not output.exists()


@pytest.mark.parametrize("missing", [
    "products/deployment-kit/docs/prebuilt/README.md",
    "products/deployment-kit/docs/prebuilt/install.md",
    "products/deployment-kit/docs/prebuilt/deploy-gitlab-pages.md",
    "products/deployment-kit/docs/prebuilt/deploy-static-hosting.md",
    "products/deployment-kit/ci/gitlab/prebuilt/.gitlab-ci.yml",
    "products/deployment-kit/scripts/verify_prebuilt.py",
    MANIFEST_SCHEMA_PATH.as_posix(),
])
def test_build_release_rejects_missing_packaging_input(tmp_path: Path, missing: str):
    repo, site = _release_fixture(tmp_path)
    (repo / missing).unlink()
    output = tmp_path / "release"

    with pytest.raises(ReleaseError, match="missing"):
        _build(repo, site, output)

    assert not output.exists()


@pytest.mark.parametrize("version", ["../escape", "v1.2.3", "1.2", "01.2.3", "1.2.3-01", "1.2.3\n"])
def test_build_release_rejects_invalid_version_before_writing(tmp_path: Path, version: str):
    repo, site = _release_fixture(tmp_path)
    output = tmp_path / "release"

    with pytest.raises(ReleaseError, match="SemVer"):
        _build(repo, site, output, version=version)

    assert not output.exists()


def test_build_release_preserves_semver_suffix_and_is_reproducible(tmp_path: Path):
    repo, site = _release_fixture(tmp_path)
    version = "1.2.3-rc.1+build.2"

    first = _build(repo, site, tmp_path / "first", version=version)
    second = _build(repo, site, tmp_path / "second", version=version)

    assert first[0].name == f"deployment-kit-prebuilt-{version}.tar.gz"
    assert [path.read_bytes() for path in first] == [path.read_bytes() for path in second]


def _extracted_package(tmp_path: Path) -> Path:
    repo, site = _release_fixture(tmp_path)
    built = _build(repo, site, tmp_path / "release")
    with tarfile.open(built[0], "r:gz") as archive:
        archive.extractall(tmp_path / "extracted", filter="data")
    return tmp_path / "extracted" / f"deployment-kit-prebuilt-{VERSION}"


def _customer_commands(package: Path) -> list[str]:
    ci = yaml.safe_load((package / ".gitlab-ci.yml").read_text(encoding="utf-8"))
    install = (package / "docs/install.md").read_text(encoding="utf-8")
    install_commands = [
        line for block in re.findall(r"```sh\n(.*?)```", install, flags=re.DOTALL)
        for line in block.splitlines() if line.startswith("python3 ") and "--expected-version" not in line
    ]
    assert install_commands, "the delivered installation guide must provide its verification command"
    return [*install_commands, *ci["pages"]["script"]]


def _run_customer_command(package: Path, command: str) -> subprocess.CompletedProcess:
    args = shlex.split(command)
    assert args[0] == "python3", "these tests execute the shipped Python command, not arbitrary shell code"
    return subprocess.run(
        [sys.executable, *args[1:]], cwd=package, capture_output=True, text=True, check=False,
    )


def _assert_customer_checks(package: Path, *, error: str | None = None) -> None:
    # Execute commands from both delivered documents; don't reproduce verifier logic here.
    results = [_run_customer_command(package, command) for command in _customer_commands(package)]
    assert len(results) == 2
    for result in results:
        if error is None:
            assert result.returncode == 0, result.stderr
            assert "Prebuilt package verified" in result.stdout
        else:
            assert result.returncode != 0
            assert error in result.stderr, result.stderr
    assert (results[0].returncode, results[0].stdout, results[0].stderr) == (
        results[1].returncode, results[1].stdout, results[1].stderr
    )


def _save_manifest(package: Path, manifest: dict) -> None:
    (package / "release-manifest.json").write_text(json.dumps(manifest) + "\n", encoding="utf-8")


def _refresh_checksums(package: Path) -> None:
    """Keep metadata consistent so negative tests reach content/reference validation."""
    manifest = json.loads((package / "release-manifest.json").read_text(encoding="utf-8"))
    contents = {
        path.relative_to(package).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in package.rglob("*")
        if path.is_file() and path not in {package / "release-manifest.json", package / "SHA256SUMS.txt"}
    }
    manifest["artifacts"] = [{"path": name, "sha256": f"sha256:{digest}"} for name, digest in sorted(contents.items())]
    _save_manifest(package, manifest)
    (package / "SHA256SUMS.txt").write_text(
        "".join(f"{digest}  {name}\n" for name, digest in sorted(contents.items())), encoding="utf-8",
    )


def test_delivered_verification_accepts_extracted_package_without_modifying_it(tmp_path: Path):
    package = _extracted_package(tmp_path)
    before = {path.relative_to(package): path.read_bytes() for path in package.rglob("*") if path.is_file()}

    _assert_customer_checks(package)

    after = {path.relative_to(package): path.read_bytes() for path in package.rglob("*") if path.is_file()}
    assert after == before
    ci = yaml.safe_load((package / ".gitlab-ci.yml").read_text(encoding="utf-8"))
    assert ci["pages"]["artifacts"]["paths"] == ["public/"]


def test_delivered_verification_accepts_renamed_git_checkout(tmp_path: Path):
    package = _extracted_package(tmp_path)
    customer = tmp_path / "customer-pages"
    # Copy real package files into a separately named checkout, without moving or deleting originals.
    copy_release_tree(package, customer)
    _write(customer / ".git/config", b"[core]\nrepositoryformatversion = 0\n")

    _assert_customer_checks(customer)


@pytest.mark.parametrize("timestamp", [
    "2026-09-09 10:00:00+00:00", "2026-09-09T10:00:00+01:60", "2026-09-09T10:00:00+24:00",
    "2026-09-09T24:00:00Z", "2026-02-29T10:00:00Z", "2026-09-09T10:00:00", "not-a-date",
])
def test_both_customer_paths_reject_invalid_timestamps(tmp_path: Path, timestamp: str):
    package = _extracted_package(tmp_path)
    manifest = json.loads((package / "release-manifest.json").read_text(encoding="utf-8"))
    manifest["created_at"] = timestamp
    _save_manifest(package, manifest)

    _assert_customer_checks(package, error="date-time")


@pytest.mark.parametrize("timestamp", [
    "2026-09-09T10:00:00Z", "2026-09-09T10:00:00.1234567+05:45", "2024-02-29t10:00:00z",
])
def test_both_customer_paths_accept_valid_timestamps(tmp_path: Path, timestamp: str):
    package = _extracted_package(tmp_path)
    manifest = json.loads((package / "release-manifest.json").read_text(encoding="utf-8"))
    manifest["created_at"] = timestamp
    _save_manifest(package, manifest)

    _assert_customer_checks(package)


@pytest.mark.parametrize(("field", "value", "error"), [
    ("source_revision", "", "too short"), ("produces", [], "must be a object"),
    ("produces", {"release_manifest": []}, "too few items"),
    ("produces", {"release_manifest": ["v1", "v1"]}, "duplicate items"),
    ("components", {"site": ""}, "too short"), ("unexpected", True, "unexpected field"),
    ("product", "skill-catalog", "not for deployment-kit-prebuilt"),
])
def test_both_customer_paths_validate_manifest_schema(tmp_path: Path, field: str, value, error: str):
    package = _extracted_package(tmp_path)
    manifest = json.loads((package / "release-manifest.json").read_text(encoding="utf-8"))
    manifest[field] = value
    _save_manifest(package, manifest)

    _assert_customer_checks(package, error=error)


@pytest.mark.parametrize(("change", "error"), [
    ("tamper", "checksum mismatch"), ("missing", "missing required package files"),
    ("extra", "file list does not match"), ("mismatched-checksums", "do not match"),
    ("duplicate-checksum", "duplicate checksum path"), ("bad-checksum", "invalid checksum entry"),
    ("duplicate-manifest", "duplicate items"), ("duplicate-json", "duplicate JSON field"),
    ("unsupported-schema", "unsupported release-manifest schema"),
])
def test_both_customer_paths_reject_damaged_package(tmp_path: Path, change: str, error: str):
    package = _extracted_package(tmp_path)
    if change == "tamper":
        _write(package / "public/assets/site.css", b"tampered\n")
    elif change == "missing":
        (package / "public/index.html").unlink()
    elif change == "extra":
        _write(package / "public/extra.txt")
    elif change in {"mismatched-checksums", "duplicate-checksum", "bad-checksum"}:
        checksum_file = package / "SHA256SUMS.txt"
        lines = checksum_file.read_text(encoding="utf-8").splitlines()
        if change == "mismatched-checksums":
            lines[0] = "0" * 64 + lines[0][64:]
        elif change == "duplicate-checksum":
            lines.append(lines[0])
        else:
            lines[0] = "not a checksum"
        checksum_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    elif change == "duplicate-manifest":
        manifest = json.loads((package / "release-manifest.json").read_text(encoding="utf-8"))
        manifest["artifacts"].append(manifest["artifacts"][0])
        _save_manifest(package, manifest)
    elif change == "duplicate-json":
        manifest_file = package / "release-manifest.json"
        text = manifest_file.read_text(encoding="utf-8")
        manifest_file.write_text('{"product":"ignored",' + text[1:], encoding="utf-8")
    else:
        schema_path = package / MANIFEST_SCHEMA_PATH
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        schema["properties"]["version"]["maxLength"] = 100
        schema_path.write_text(json.dumps(schema), encoding="utf-8")
        _refresh_checksums(package)

    _assert_customer_checks(package, error=error)


@pytest.mark.parametrize(("name", "content"), [
    ("page.html", '<a href=downloads/missing.zip>Download</a>'),
    ("page.html", '<img src="downloads&#47;missing.zip">'),
    ("data.json", r'{"nested":[{"download":"downloads\/missing.zip"}]}'),
    ("data.json", r'{"download":"downloads\u002fmissing.zip"}'),
    ("script.js", r'const download = "downloads\/missing.zip";'),
    ("script.js", r"const download = 'downloads\x2fmissing.zip';"),
    ("script.js", r'const pattern = /https?:\/\//; const download = "downloads/missing.zip";'),
    ("script.js", 'const download = `downloads/missing.zip`;'),
    ("page.html", r'<script type="application/json">{"download":"downloads\/missing.zip"}</script>'),
])
def test_both_customer_paths_find_missing_static_downloads(tmp_path: Path, name: str, content: str):
    package = _extracted_package(tmp_path)
    _write(package / "public" / name, content.encode())
    _refresh_checksums(package)

    _assert_customer_checks(package, error="missing referenced download")


@pytest.mark.parametrize("inline", [False, True])
@pytest.mark.parametrize("prefix", [
    'const quote = /"/g;',
    "const quote = /'/g;",
    r'''const quote = /["'`/]/g;''',
    r'''const quote = /[\]"/]/g;''',
    r'''const quote = /\"\//g;''',
    'const quote = /* pattern */ /"/g;',
    'function quote() { return /"/g; }',
    'if (ready()) /"/g.test(value);',
    'if (ready) { work(); } /"/g.test(value);',
])
def test_both_customer_paths_find_download_after_regex(tmp_path: Path, inline: bool, prefix: str):
    package = _extracted_package(tmp_path)
    script = prefix + ' const url = "downloads/missing.zip";'
    content = f"<script>{script}</script>" if inline else script
    _write(package / "public" / ("regex.html" if inline else "regex.js"), content.encode())
    _refresh_checksums(package)

    _assert_customer_checks(package, error="missing referenced download")


@pytest.mark.parametrize("script", [
    'const ratio = 8 / 2; const url = "downloads/missing.zip";',
    'const ratio = numerator / "downloads/missing.zip" / denominator;',
    'const ratio = (numerator) / "downloads/missing.zip" / denominator;',
    'const ratio = values[0] / "downloads/missing.zip" / denominator;',
    'const ratio = {value: 1} / "downloads/missing.zip" / denominator;',
    'const ratio = counter++ / "downloads/missing.zip" / denominator;',
    'const ratio = function() {} / "downloads/missing.zip" / denominator;',
])
def test_both_customer_paths_find_download_among_division_operators(tmp_path: Path, script: str):
    package = _extracted_package(tmp_path)
    _write(package / "public/division.js", script.encode())
    _refresh_checksums(package)

    _assert_customer_checks(package, error="missing referenced download")


def test_both_customer_paths_ignore_regex_contents_without_losing_real_links(tmp_path: Path):
    package = _extracted_package(tmp_path)
    _write(package / "public/regex.js", br'''
const pattern = /"downloads\/not-a-file.zip"/g;
const quote = /["'`/]/g;
// "downloads/comment-not-a-file.zip"
/* 'downloads/comment-not-a-file.zip' */
const text = 'Example text containing "downloads/not-a-file.zip"';
const url = "downloads/example.zip";
''')
    _refresh_checksums(package)

    _assert_customer_checks(package)


@pytest.mark.parametrize("reference", [
    "downloads/../index.html", "downloads/%2e%2e/index.html", "downloads/%2Fetc/passwd",
    "downloads/%5c..%5cindex.html", "downloads/C:/secret", "downloads/%00.zip",
])
def test_both_customer_paths_reject_unsafe_downloads(tmp_path: Path, reference: str):
    package = _extracted_package(tmp_path)
    _write(package / "public/data.json", json.dumps({"download": reference}).encode())
    _refresh_checksums(package)

    _assert_customer_checks(package, error="unsafe package path")


def test_verifier_accepts_decoded_existing_downloads_and_ignores_dynamic_references(tmp_path: Path):
    package = _extracted_package(tmp_path)
    _write(package / "public/links.html", b'<a href=./downloads/example.zip?q=ignored#section>Download</a>')
    _write(package / "public/links.json", br'{"download":"downloads\/example.zip?version=1#section"}')
    _write(package / "public/links.js", br'''
// "downloads/comment-not-a-file.zip"
/* 'downloads/comment-not-a-file.zip' */
const known = "downloads\u002fexample.zip";
const constructed = 'downloads/' + name;
const templated = `downloads/${name}.zip`;
const unrelated = "http://[invalid-URL-example";
''')
    _refresh_checksums(package)

    _assert_customer_checks(package)


def test_verifier_rejects_missing_download_even_when_metadata_agrees(tmp_path: Path):
    package = _extracted_package(tmp_path)
    (package / "public/downloads/example.zip").unlink()
    _refresh_checksums(package)

    _assert_customer_checks(package, error="missing referenced download")


def test_both_customer_paths_reject_root_absolute_download(tmp_path: Path):
    package = _extracted_package(tmp_path)
    _write(package / "public/index.html", b'<a href="/downloads/example.zip">Download</a>')
    _refresh_checksums(package)

    _assert_customer_checks(package, error="download URL must be relative")


@pytest.mark.parametrize("relative", ["../outside.txt", "/outside.txt", "C:/outside.txt", "public\\outside.txt"])
def test_both_customer_paths_reject_unsafe_manifest_paths(tmp_path: Path, relative: str):
    package = _extracted_package(tmp_path)
    manifest = json.loads((package / "release-manifest.json").read_text(encoding="utf-8"))
    manifest["artifacts"][0]["path"] = relative
    _save_manifest(package, manifest)

    for command in _customer_commands(package):
        result = _run_customer_command(package, command)
        assert result.returncode != 0
        assert "unsafe package path" in result.stderr or "required pattern" in result.stderr


def test_both_customer_paths_reject_required_file_omitted_from_metadata(tmp_path: Path):
    package = _extracted_package(tmp_path)
    manifest = json.loads((package / "release-manifest.json").read_text(encoding="utf-8"))
    manifest["artifacts"] = [entry for entry in manifest["artifacts"] if entry["path"] != "README.md"]
    _save_manifest(package, manifest)
    checksum = package / "SHA256SUMS.txt"
    lines = [line for line in checksum.read_text(encoding="utf-8").splitlines() if not line.endswith("  README.md")]
    checksum.write_text("\n".join(lines) + "\n", encoding="utf-8")

    _assert_customer_checks(package, error="manifest file list does not match")


@pytest.mark.parametrize("kind", ["symlink", "junction"])
def test_both_customer_paths_reject_added_directory_links(tmp_path: Path, make_link, kind: str):
    package = _extracted_package(tmp_path)
    outside = tmp_path / "outside"
    _write(outside / "private.txt")
    make_link(package / "public/linked", outside, kind=kind)

    _assert_customer_checks(package, error="package must not contain links")


def test_install_version_check_matches_selected_archive(tmp_path: Path):
    package = _extracted_package(tmp_path)
    command = _customer_commands(package)[0]

    valid = _run_customer_command(package, f"{command} --expected-version {VERSION}")
    invalid = _run_customer_command(package, f"{command} --expected-version 9.9.9")

    assert valid.returncode == 0, valid.stderr
    assert invalid.returncode != 0
    assert "expected archive version" in invalid.stderr


def _run_ci_prebuilt(repo: Path, tmp_path: Path):
    """Run only the packaging step; Python tests never invoke Node or npm."""
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("Bash is required to execute the GitHub-hosted packaging step")
    subprocess.run([bash, "--version"], check=True, capture_output=True, text=True)
    workflow = yaml.safe_load((REPOSITORY_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
    steps = workflow["jobs"]["static-site"]["steps"]
    packaging = next(step for step in steps if step.get("id") == "prebuilt")
    upload = next(step for step in steps if step.get("uses", "").startswith("actions/upload-artifact@"))
    assert steps.index(packaging) < steps.index(upload)
    assert "if" not in upload, "upload must retain the default success-only condition"
    context = {"github.run_id": "42", "github.run_attempt": "2", "github.sha": SOURCE_REVISION}

    def render(value: str) -> str:
        return re.sub(r"\$\{\{\s*(.*?)\s*\}\}", lambda match: context[match[1]], value)

    # Use the real builder and deployment inputs with an already-built fixture site.
    for filename in ("__init__.py", "release.py"):
        _write(repo / "scripts/skill_exchange" / filename,
               (REPOSITORY_ROOT / "scripts/skill_exchange" / filename).read_bytes())
    runner_temp = tmp_path / "runner temp"
    runner_temp.mkdir()
    output = tmp_path / "github-output"
    _write(output, b"")
    env = {
        **os.environ,
        **{key: render(value) for key, value in packaging["env"].items()},
        "RUNNER_TEMP": runner_temp.as_posix(),
        "GITHUB_OUTPUT": output.as_posix(),
        "SKLC_TEST_PYTHON": Path(sys.executable).as_posix(),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    # Windows names its interpreter python.exe. Map both runner command names to
    # the active test interpreter without changing the workflow's shell script.
    python_commands = 'python() { "$SKLC_TEST_PYTHON" "$@"; }\npython3() { "$SKLC_TEST_PYTHON" "$@"; }\n'
    if os.name == "nt":
        # Git Bash utilities expect /c/... paths; native Python receives Windows
        # paths via MSYS argument conversion. Do not change the Ubuntu workflow.
        python_commands += 'export RUNNER_TEMP="$(cygpath -u "$RUNNER_TEMP")"\n'
    result = subprocess.run(
        [bash, "--noprofile", "--norc", "-e", "-o", "pipefail", "-c", python_commands + packaging["run"]],
        cwd=repo, env=env, capture_output=True, text=True, check=False, timeout=60,
    )
    outputs = dict(line.split("=", 1) for line in output.read_text(encoding="utf-8").splitlines())
    context.update({f"steps.prebuilt.outputs.{key}": value for key, value in outputs.items()})
    upload_root = None
    if result.returncode == 0:
        upload_path = render(upload["with"]["path"])
        if os.name == "nt":
            upload_path = subprocess.run(
                [bash, "--noprofile", "--norc", "-c", 'cygpath -w -- "$1"', "ci-upload-path", upload_path],
                env=env, check=True, capture_output=True, text=True,
            ).stdout.strip()
        upload_root = Path(upload_path)
    return result, outputs, upload_root, upload["with"]


def test_ci_download_is_complete_and_passes_its_delivered_verification(tmp_path: Path):
    repo, _site = _release_fixture(tmp_path)

    result, _outputs, upload_root, upload = _run_ci_prebuilt(repo, tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Prebuilt package verified" in result.stdout
    assert upload_root is not None and upload_root.is_relative_to(tmp_path / "runner temp")
    # Model the configured directory upload as a ZIP, including its hidden-file
    # setting. This checks the layout, not GitHub's remote artifact service.
    archive_path = tmp_path / "static-site.zip"
    with ZipFile(archive_path, "w") as archive:
        for path in upload_root.rglob("*"):
            relative = path.relative_to(upload_root)
            include_hidden = str(upload.get("include-hidden-files", False)).lower() == "true"
            if not include_hidden and any(part.startswith(".") for part in relative.parts):
                continue
            archive.write(path, relative.as_posix())
    customer = tmp_path / "customer-project"
    with ZipFile(archive_path) as archive:
        names = set(archive.namelist())
        assert {"public/index.html", "scripts/verify_prebuilt.py", ".gitlab-ci.yml", "README.md",
                "docs/install.md", MANIFEST_SCHEMA_PATH.as_posix(), "release-manifest.json", "SHA256SUMS.txt"} <= names
        assert "index.html" not in names
        assert not any(name.endswith(".tar.gz") for name in names)
        archive.extractall(customer)
    _assert_customer_checks(customer)
    manifest = json.loads((customer / "release-manifest.json").read_text(encoding="utf-8"))
    assert manifest["version"] == "0.0.0-ci.42.2"
    assert manifest["source_revision"] == SOURCE_REVISION
    assert manifest["product"] == "deployment-kit-prebuilt"
    assert not (customer / "public/.gitkeep").exists()


@pytest.mark.parametrize("broken", [
    "missing-download", "absolute-download", "missing-detail", "empty-home", "missing-doc",
])
def test_ci_rejects_incomplete_packages_before_exposing_an_upload_path(tmp_path: Path, broken: str):
    repo, site = _release_fixture(tmp_path)
    if broken == "missing-download":
        _write(site / "index.html", b'<a href="downloads/not-packaged.zip">Missing</a>\n')
    elif broken == "absolute-download":
        _write(site / "index.html", b'<a href="/downloads/example.zip">Absolute</a>\n')
    elif broken == "missing-detail":
        (site / "skills/example/index.html").unlink()
    elif broken == "empty-home":
        _write(site / "index.html", b"")
    else:
        (repo / "products/deployment-kit/docs/prebuilt/install.md").unlink()

    result, outputs, upload_root, _upload = _run_ci_prebuilt(repo, tmp_path)

    assert result.returncode != 0
    assert outputs == {}
    assert upload_root is None
    if broken == "missing-download":
        assert "missing referenced download" in result.stderr
    elif broken == "absolute-download":
        assert "download URL must be relative" in result.stderr
    elif broken in {"missing-detail", "empty-home"}:
        assert "Prebuilt package verified" in result.stdout
    else:
        assert "required release file is missing" in result.stderr and "install.md" in result.stderr


@pytest.mark.parametrize("version", [VERSION, "1.2.3-rc.1+build.7"])
@pytest.mark.parametrize("fence", ["```", "~~~~"])
def test_release_notes_select_exact_version_and_preserve_subsections(tmp_path: Path, version: str, fence: str):
    notes = tmp_path / "RELEASE_NOTES.md"
    accepted = f"## {version}\n\n- Portable prebuilt download.\n\n### Compatibility\n\n- Python 3.12+.\n"
    _write(notes, (
        f"# Release Notes\n\n{fence}markdown\n## {version}\nExample only.\n{fence}\n\n"
        f"## 9.0.0\n\nLater release.\n\n{accepted}\n## 0.1.0\n\nEarlier release.\n"
    ).encode())

    assert extract_release_notes(notes, version) == accepted


@pytest.mark.parametrize("contents,error", [
    ("# Release Notes\n", "exactly one heading"),
    ("## 1.2.30\nWrong version.\n", "exactly one heading"),
    ("## 1.2.3\nFirst.\n## 1.2.3\nSecond.\n", "exactly one heading"),
    ("## 1.2.3\n\n## 1.0.0\nOld notes.\n", "empty"),
    ("## 1.2.3\n \t\n", "empty"),
    ("````markdown\n```\n## 1.2.3\nExample only.\n````\n", "exactly one heading"),
])
def test_release_notes_reject_missing_ambiguous_or_empty_sections(tmp_path: Path, contents: str, error: str):
    notes = tmp_path / "RELEASE_NOTES.md"
    _write(notes, contents.encode())

    with pytest.raises(ReleaseError, match=error):
        extract_release_notes(notes, VERSION)


def test_release_notes_reject_missing_file(tmp_path: Path):
    with pytest.raises(ReleaseError, match="missing"):
        extract_release_notes(tmp_path / "RELEASE_NOTES.md", VERSION)


@pytest.mark.parametrize("kind", ["symlink", "junction"])
def test_release_notes_reject_linked_source(tmp_path: Path, make_link, kind: str):
    outside = tmp_path / "outside"
    _write(outside / "RELEASE_NOTES.md", b"## 1.2.3\nOutside notes.\n")
    linked = tmp_path / "linked"
    make_link(linked, outside, kind=kind)

    with pytest.raises(ReleaseError, match="link"):
        extract_release_notes(linked / "RELEASE_NOTES.md", VERSION)


def _run_release_workflow(repo: Path, tmp_path: Path, *, version: str = VERSION,
                          broken: str | None = None, annotated: bool = False):
    """Execute release shell steps against a temporary Git repo; never call GitHub.

    Dependency installation, assessment-data generation and Node builds are not
    invoked by Python tests. The site here is already built by the test fixture.
    """
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("Bash is required to execute the GitHub-hosted release steps")
    workflow = yaml.safe_load((REPOSITORY_ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8"))
    job = workflow["jobs"]["release"]
    steps = [step for step in job["steps"] if step.get("id") in {
        "release-inputs", "release-assets", "publish-release",
    }]
    assert [step["id"] for step in steps] == ["release-inputs", "release-assets", "publish-release"]
    assert all("if" not in step for step in steps), "release steps must remain success-only"
    for filename in ("__init__.py", "release.py"):
        _write(repo / "scripts/skill_exchange" / filename,
               (REPOSITORY_ROOT / "scripts/skill_exchange" / filename).read_bytes())
    shutil.copytree(
        REPOSITORY_ROOT / "products/assessment-kit",
        repo / "products/assessment-kit",
    )
    for contract in ("skill-package", "boe", "assessment-artifacts", "release-manifest"):
        shutil.copytree(
            REPOSITORY_ROOT / "contracts" / contract / "v1",
            repo / "contracts" / contract / "v1",
            dirs_exist_ok=True,
        )
    notes = f"## {version}\n\n- Ready-to-deploy site.\n"
    if broken == "missing-notes":
        notes = "## 0.1.0\n\nEarlier release.\n"
    elif broken == "empty-notes":
        notes = f"## {version}\n\n"
    elif broken == "duplicate-notes":
        notes += notes
    _write(repo / "RELEASE_NOTES.md", ("# Release Notes\n\n" + notes).encode())
    runner_temp = tmp_path / "runner temp"
    runner_temp.mkdir()
    env_file = tmp_path / "github-env"
    _write(env_file, b"")
    recorded = tmp_path / "recorded-release.json"
    recorder = tmp_path / "record_release.py"
    _write(recorder, b"""import json
import os
import sys
from pathlib import Path

args = sys.argv[1:]
assert args[:2] == ['release', 'create']
body = Path(args[args.index('--notes-file') + 1]).read_text(encoding='utf-8')
Path(os.environ['SKLC_RECORDED_RELEASE']).write_text(
    json.dumps({'args': args, 'body': body}), encoding='utf-8')
""")
    env = {
        **os.environ, **job["env"],
        "RUNNER_TEMP": runner_temp.as_posix(), "GITHUB_ENV": env_file.as_posix(),
        "GITHUB_REF_TYPE": "tag", "GITHUB_REF_NAME": f"v{version}", "GITHUB_REF": f"refs/tags/v{version}",
        "SKLC_TEST_PYTHON": Path(sys.executable).as_posix(),
        "SKLC_RELEASE_RECORDER": recorder.as_posix(), "SKLC_RECORDED_RELEASE": recorded.as_posix(),
        "PYTHONDONTWRITEBYTECODE": "1", "GH_TOKEN": "", "GITHUB_TOKEN": "",
        "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_TERMINAL_PROMPT": "0",
    }

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", "-c", "user.name=Release Test", "-c", "user.email=release-test@example.invalid",
             "-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false", *args],
            cwd=repo, env=env, check=True, capture_output=True, text=True, timeout=30,
        ).stdout.strip()

    # These commits/tags exist only in this disposable, remote-free test repo.
    git("init", "-q")
    if broken == "untracked-notes":
        _write(repo / "fixture.txt")
        git("add", "fixture.txt")
    else:
        git("add", "RELEASE_NOTES.md")
    git("commit", "-q", "-m", "Accepted fixture notes")
    revision = git("rev-parse", "HEAD")
    if annotated:
        git("tag", "-a", f"v{version}", "-m", "Fixture release")
        assert git("rev-parse", f"v{version}") != revision
    else:
        git("tag", f"v{version}")
    if broken == "dirty-notes":
        _write(repo / "RELEASE_NOTES.md", b"## 1.2.3\nUncommitted notes.\n")
    elif broken == "wrong-commit":
        git("commit", "--allow-empty", "-q", "-m", "Not the tagged commit")
    elif broken == "invalid-tag":
        env["GITHUB_REF_NAME"] = "v01.2.3"
    elif broken == "missing-download":
        _write(repo / "site/dist/index.html", b'<a href="downloads/missing.zip">Missing</a>')

    # A shell function always shadows gh, even if a real authenticated CLI is
    # installed. It records arguments and notes instead of publishing anything.
    prefix = (
        'python() { "$SKLC_TEST_PYTHON" "$@"; }\n'
        'python3() { "$SKLC_TEST_PYTHON" "$@"; }\n'
        'gh() { python "$SKLC_RELEASE_RECORDER" "$@"; }\n'
    )
    if os.name == "nt":
        prefix += 'export RUNNER_TEMP="$(cygpath -u "$RUNNER_TEMP")"\n'
    results = []
    for step in steps:
        if step["id"] == "release-assets":
            release_directory = Path(env["RELEASE_DIR"])
            wheel_version = version.replace("-rc.", "rc").replace("-", ".")
            wheel = release_directory / "wheels" / f"skill_assessment-{wheel_version}-py3-none-any.whl"
            wheel.parent.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(wheel, "w") as archive:
                archive.writestr(
                    f"skill_assessment-{wheel_version}.dist-info/METADATA",
                    f"Metadata-Version: 2.4\nName: skill-assessment\nVersion: {wheel_version}\n",
                )
        result = subprocess.run(
            [bash, "--noprofile", "--norc", "-e", "-o", "pipefail", "-c", prefix + step["run"]],
            cwd=repo, env=env, capture_output=True, text=True, check=False, timeout=60,
        )
        results.append(result)
        if result.returncode != 0:
            break
        env.update(dict(line.split("=", 1) for line in env_file.read_text(encoding="utf-8").splitlines()))
    record = json.loads(recorded.read_text(encoding="utf-8")) if recorded.exists() else None
    return results, record, revision


@pytest.mark.parametrize("version,annotated,prerelease", [
    (VERSION, False, False), (VERSION, True, False),
    ("1.2.3-rc.1+build.7", True, True), ("1.2.3+build-test", False, False),
])
def test_release_workflow_verifies_and_publishes_releasable_product_assets(
    tmp_path: Path, version: str, annotated: bool, prerelease: bool,
):
    repo, _site = _release_fixture(tmp_path)

    results, record, revision = _run_release_workflow(repo, tmp_path, version=version, annotated=annotated)

    assert len(results) == 3
    assert all(result.returncode == 0 for result in results), "\n".join(r.stdout + r.stderr for r in results)
    assert "Prebuilt package verified" in results[1].stdout
    assert f"deployment-kit-prebuilt-{version}.release-manifest.json: OK" in results[1].stdout
    assert f"assessment-kit-{version}.release-manifest.json: OK" in results[1].stdout
    assert record is not None
    args = record["args"]
    assert args[:3] == ["release", "create", f"v{version}"]
    assets = [Path(value) for value in args[3:9]]
    assert [path.name for path in assets] == [
        f"deployment-kit-prebuilt-{version}.tar.gz",
        f"deployment-kit-prebuilt-{version}.release-manifest.json",
        f"deployment-kit-prebuilt-{version}.SHA256SUMS.txt",
        f"assessment-kit-{version}.tar.gz",
        f"assessment-kit-{version}.release-manifest.json",
        f"assessment-kit-{version}.SHA256SUMS.txt",
    ]
    assert set(assets[0].parent.iterdir()) == set(assets)
    assert args[9:13] == ["--verify-tag", "--title", f"v{version}", "--notes-file"]
    assert args[14:] == (["--prerelease"] if prerelease else [])
    assert record["body"] == f"## {version}\n\n- Ready-to-deploy site.\n"
    assert Path(args[13]).parent != assets[0].parent
    manifest = json.loads(assets[1].read_text(encoding="utf-8"))
    assert manifest["source_revision"] == revision
    assert manifest["version"] == version
    assert _checksums(assets[2]) == {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in assets[:2]
    }
    with tarfile.open(assets[3], "r:gz") as assessment_archive:
        internal_manifest = assessment_archive.extractfile(
            f"assessment-kit-{version}/release-manifest.json"
        )
        assert internal_manifest is not None
        assert assets[4].read_bytes() == internal_manifest.read()
    assert _checksums(assets[5]) == {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in assets[3:5]
    }
    customer = tmp_path / "customer"
    with tarfile.open(assets[0]) as archive:
        archive.extractall(customer, filter="data")
    _assert_customer_checks(customer / f"deployment-kit-prebuilt-{version}")


@pytest.mark.parametrize("broken,error", [
    ("missing-notes", "exactly one heading"), ("empty-notes", "empty"),
    ("duplicate-notes", "exactly one heading"), ("dirty-notes", "Uncommitted notes"),
    ("untracked-notes", "did not match any file"),
    ("wrong-commit", None), ("invalid-tag", "version must be a SemVer value"),
    ("missing-download", "missing referenced download"),
])
def test_release_workflow_stops_before_publishing_invalid_inputs(tmp_path: Path, broken: str, error: str | None):
    repo, _site = _release_fixture(tmp_path)

    results, record, _revision = _run_release_workflow(repo, tmp_path, broken=broken)

    assert results[-1].returncode != 0
    assert len(results) == (2 if broken == "missing-download" else 1)
    assert record is None, "an invalid release must never reach the publish command"
    if error is not None:
        assert error in results[-1].stdout + results[-1].stderr
