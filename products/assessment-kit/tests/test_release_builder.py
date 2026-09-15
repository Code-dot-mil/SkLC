from __future__ import annotations

import hashlib
import json
import tarfile
import zipfile
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from release_tools.build import assemble_release

REPOSITORY_ROOT = Path(__file__).parents[3]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_checksums(path: Path) -> dict[str, str]:
    return {line.split("  ", 1)[1]: line.split("  ", 1)[0] for line in path.read_text().splitlines()}


def make_wheel(path: Path, version: str = "0.1.0") -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            f"skill_assessment-{version}.dist-info/METADATA",
            f"Metadata-Version: 2.4\nName: skill-assessment\nVersion: {version}\n",
        )
    return path


def test_release_archive_and_two_layer_checksums_follow_contract(tmp_path: Path):
    wheel = make_wheel(tmp_path / "skill_assessment-0.1.0-py3-none-any.whl")
    output = tmp_path / "release"

    archive, external_manifest, external_checksums = assemble_release(
        repository_root=REPOSITORY_ROOT,
        version="0.1.0",
        source_revision="a" * 40,
        created_at="2026-09-10T16:00:00Z",
        wheel=wheel,
        output_directory=output,
    )

    external = parse_checksums(external_checksums)
    assert external == {archive.name: sha256(archive), external_manifest.name: sha256(external_manifest)}

    extracted = tmp_path / "extracted"
    with tarfile.open(archive, "r:gz") as handle:
        handle.extractall(extracted, filter="data")
    root = extracted / "assessment-kit-0.1.0"
    assert (root / "release-manifest.json").read_bytes() == external_manifest.read_bytes()

    manifest = json.loads(external_manifest.read_text())
    schema = json.loads((root / "contracts/release-manifest/v1/release-manifest.schema.json").read_text())
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(manifest)
    paths = [entry["path"] for entry in manifest["artifacts"]]
    assert paths == sorted(paths)
    assert "release-manifest.json" not in paths
    assert "SHA256SUMS.txt" not in paths
    assert archive.name not in paths
    assert "dist/skill_assessment-0.1.0-py3-none-any.whl" in paths
    assert "docs/install.md" in paths
    assert "contracts/boe/v1/boe.schema.json" in paths

    expected_internal = {}
    for entry in manifest["artifacts"]:
        artifact = root / entry["path"]
        assert entry["sha256"] == f"sha256:{sha256(artifact)}"
        expected_internal[entry["path"]] = sha256(artifact)
    assert parse_checksums(root / "SHA256SUMS.txt") == expected_internal


def test_release_assembly_is_byte_deterministic(tmp_path: Path):
    wheel = make_wheel(tmp_path / "skill_assessment-0.1.0-py3-none-any.whl")
    common = {
        "repository_root": REPOSITORY_ROOT,
        "version": "0.1.0",
        "source_revision": "b" * 40,
        "created_at": "2026-09-10T16:00:00Z",
        "wheel": wheel,
    }

    first = assemble_release(**common, output_directory=tmp_path / "first")
    second = assemble_release(**common, output_directory=tmp_path / "second")

    assert [path.read_bytes() for path in first] == [path.read_bytes() for path in second]


def test_release_accepts_python_normalized_prerelease_wheel_version(tmp_path: Path):
    wheel = make_wheel(
        tmp_path / "skill_assessment-1.2.3rc1+build.7-py3-none-any.whl",
        "1.2.3rc1+build.7",
    )

    assets = assemble_release(
        repository_root=REPOSITORY_ROOT,
        version="1.2.3-rc.1+build.7",
        source_revision="c" * 40,
        created_at="2026-09-10T16:00:00Z",
        wheel=wheel,
        output_directory=tmp_path / "release",
    )

    manifest = json.loads(assets[1].read_text())
    assert manifest["version"] == "1.2.3-rc.1+build.7"
    assert manifest["components"]["skill-assessment"] == "1.2.3rc1+build.7"


@pytest.mark.parametrize("release_version,wheel_version", [
    ("1.23.4", "12.3.4"), ("1.2.34", "1.23.4"),
    ("1.2.3-rc.12", "1.2.3rc1"), ("1.2.3+build.12", "1.2.3+build1.2"),
])
def test_release_rejects_different_wheel_version(tmp_path, release_version, wheel_version):
    wheel = make_wheel(tmp_path / f"skill_assessment-{wheel_version}-py3-none-any.whl", wheel_version)
    with pytest.raises(ValueError, match="does not match"):
        assemble_release(
            repository_root=REPOSITORY_ROOT, version=release_version,
            source_revision="a" * 40, created_at="2026-09-14T10:00:00Z",
            wheel=wheel, output_directory=tmp_path / "release",
        )
    assert not (tmp_path / "release").exists()


@pytest.mark.parametrize("timestamp", [
    "2026-09-14T10:00:00+01:60", "2026-09-14T10:00:00+24:00",
    "2026-09-14 10:00:00Z", "2026-02-29T10:00:00Z", "2026-09-14T24:00:00Z",
    "2026-09-14T10:00:00", "2026-09-14T10:00:00+0100",
])
def test_invalid_timestamp_cannot_be_published(tmp_path, timestamp):
    wheel = make_wheel(tmp_path / "skill_assessment-0.1.0-py3-none-any.whl")
    with pytest.raises(ValueError, match="created-at"):
        assemble_release(
            repository_root=REPOSITORY_ROOT, version="0.1.0", source_revision="a" * 40,
            created_at=timestamp, wheel=wheel, output_directory=tmp_path / "release",
        )
    assert not (tmp_path / "release").exists()


@pytest.mark.parametrize("version", ["1.2.3-1", "1.2.3-post.1"])
def test_semver_prerelease_cannot_be_published_as_python_postrelease(tmp_path, version):
    wheel = make_wheel(tmp_path / "skill_assessment-1.2.3.post1-py3-none-any.whl", "1.2.3.post1")
    with pytest.raises(ValueError, match="prerelease"):
        assemble_release(
            repository_root=REPOSITORY_ROOT, version=version, source_revision="a" * 40,
            created_at="2026-09-14T10:00:00Z", wheel=wheel, output_directory=tmp_path / "release",
        )
