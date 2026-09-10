from __future__ import annotations

import hashlib
import json
import tarfile
import zipfile
from pathlib import Path

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
