from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import shutil
import sys
import tarfile
import tempfile
import zipfile
from collections.abc import Sequence
from datetime import datetime
from email.parser import BytesParser
from pathlib import Path

PRODUCT = "assessment-kit"
PACKAGE_DISTRIBUTION = "skill_assessment"
CONTRACT_PATHS = (
    Path("skill-package/v1"),
    Path("boe/v1"),
    Path("assessment-artifacts/v1"),
    Path("release-manifest/v1"),
)
VERSION_RE = re.compile(
    r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-(?:0|[1-9][0-9]*|[0-9A-Za-z-]*[A-Za-z-][0-9A-Za-z-]*)"
    r"(?:\.(?:0|[1-9][0-9]*|[0-9A-Za-z-]*[A-Za-z-][0-9A-Za-z-]*))*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
)
REVISION_RE = re.compile(r"^[a-f0-9]{40}$")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_version(value: str) -> str:
    normalized = value.lower()
    normalized = re.sub(r"[-_.]?(alpha|a)[-_.]?", "a", normalized)
    normalized = re.sub(r"[-_.]?(beta|b)[-_.]?", "b", normalized)
    normalized = re.sub(r"[-_.]?(preview|pre|rc)[-_.]?", "rc", normalized)
    return re.sub(r"[-_.+]", "", normalized)


def _wheel_version(wheel: Path) -> str:
    try:
        with zipfile.ZipFile(wheel) as archive:
            metadata_names = [
                name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
            ]
            if len(metadata_names) != 1:
                raise ValueError("wheel must contain exactly one dist-info/METADATA file")
            metadata = BytesParser().parsebytes(archive.read(metadata_names[0]))
    except (OSError, zipfile.BadZipFile) as exc:
        raise ValueError("wheel is not a readable Python wheel archive") from exc
    if metadata.get("Name", "").lower().replace("_", "-") != "skill-assessment":
        raise ValueError("wheel metadata is not for skill-assessment")
    wheel_version = metadata.get("Version", "").strip()
    if not wheel_version:
        raise ValueError("wheel metadata is missing Version")
    expected_name = f"{PACKAGE_DISTRIBUTION}-{wheel_version.replace('-', '_')}-py3-none-any.whl"
    if wheel.name != expected_name:
        raise ValueError(f"wheel filename must match its metadata: {expected_name}")
    return wheel_version


def _validate_inputs(version: str, source_revision: str, created_at: str, wheel: Path) -> str:
    if not VERSION_RE.fullmatch(version):
        raise ValueError("version must be an explicit semantic version")
    if not REVISION_RE.fullmatch(source_revision):
        raise ValueError("source revision must be a full lowercase 40-character Git commit")
    try:
        parsed_created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("created-at must be an ISO 8601 date-time with timezone") from exc
    if parsed_created_at.tzinfo is None:
        raise ValueError("created-at must include a timezone")
    if not wheel.is_file() or wheel.is_symlink():
        raise ValueError("wheel must be a regular file")
    wheel_version = _wheel_version(wheel)
    if _canonical_version(wheel_version) != _canonical_version(version):
        raise ValueError(f"wheel version {wheel_version} does not match release version {version}")
    return wheel_version


def _reject_symlinks(path: Path) -> None:
    if path.is_symlink():
        raise ValueError(f"release source must not be a symbolic link: {path}")
    if path.is_dir():
        for child in path.rglob("*"):
            if child.is_symlink():
                raise ValueError(f"release source must not contain a symbolic link: {child}")


def _artifact_entries(package_root: Path) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for path in sorted(package_root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(package_root).as_posix()
        if relative in {"release-manifest.json", "SHA256SUMS.txt"}:
            continue
        entries.append({"path": relative, "sha256": f"sha256:{_sha256(path)}"})
    return entries


def _add_archive_tree(archive: tarfile.TarFile, package_root: Path) -> None:
    paths = [package_root, *sorted(package_root.rglob("*"))]
    for path in paths:
        relative = Path(package_root.name) / path.relative_to(package_root)
        info = archive.gettarinfo(str(path), arcname=relative.as_posix())
        info.uid = 0
        info.gid = 0
        info.uname = ""
        info.gname = ""
        info.mtime = 0
        if info.isdir():
            info.mode = 0o755
            archive.addfile(info)
        elif info.isfile():
            info.mode = 0o644
            with path.open("rb") as handle:
                archive.addfile(info, handle)
        else:
            raise ValueError(f"release input contains unsupported filesystem object: {path}")


def _write_archive(archive_path: Path, package_root: Path) -> None:
    with archive_path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w") as archive:
                _add_archive_tree(archive, package_root)


def assemble_release(
    *,
    repository_root: Path,
    version: str,
    source_revision: str,
    created_at: str,
    wheel: Path,
    output_directory: Path,
) -> tuple[Path, Path, Path]:
    wheel_version = _validate_inputs(version, source_revision, created_at, wheel)
    product_root = repository_root / "products" / "assessment-kit"
    contracts_root = repository_root / "contracts"
    required_sources = [product_root / "README.md", product_root / "docs"]
    required_sources.extend(contracts_root / relative for relative in CONTRACT_PATHS)
    missing = [str(path) for path in required_sources if not path.exists()]
    if missing:
        raise ValueError(f"release source is missing: {', '.join(missing)}")
    for source in required_sources:
        _reject_symlinks(source)

    output_directory.mkdir(parents=True, exist_ok=True)
    archive_path = output_directory / f"{PRODUCT}-{version}.tar.gz"
    manifest_path = output_directory / f"{PRODUCT}-{version}.release-manifest.json"
    checksums_path = output_directory / f"{PRODUCT}-{version}.SHA256SUMS.txt"
    existing = [path.name for path in (archive_path, manifest_path, checksums_path) if path.exists()]
    if existing:
        raise ValueError(f"refusing to overwrite release assets: {', '.join(existing)}")

    with tempfile.TemporaryDirectory(prefix="assessment-kit-release-") as temporary:
        package_root = Path(temporary) / f"{PRODUCT}-{version}"
        (package_root / "dist").mkdir(parents=True)
        (package_root / "contracts").mkdir()
        shutil.copy2(product_root / "README.md", package_root / "README.md")
        shutil.copytree(product_root / "docs", package_root / "docs")
        shutil.copy2(wheel, package_root / "dist" / wheel.name)
        for relative in CONTRACT_PATHS:
            destination = package_root / "contracts" / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(contracts_root / relative, destination)

        artifacts = _artifact_entries(package_root)
        manifest = {
            "schema_version": "skill-exchange-release-manifest/v1",
            "product": PRODUCT,
            "version": version,
            "source_revision": source_revision,
            "created_at": created_at,
            "produces": {
                "assessment_artifacts": ["skill-exchange-assessment-artifacts/v1"],
                "boe": ["skill-exchange-boe/v1"],
            },
            "consumes": {"skill_package": ["urn:skill-exchange:skill-package:v1"]},
            "artifacts": artifacts,
            "components": {
                "skill-assessment": wheel_version,
                "skillspector": "2.10.0@e29b16d305b0e738e3d4b952ba102f5522a6f084",
            },
        }
        manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
        (package_root / "release-manifest.json").write_bytes(manifest_bytes)
        internal_checksums = "".join(
            f"{entry['sha256'].removeprefix('sha256:')}  {entry['path']}\n" for entry in artifacts
        ).encode()
        (package_root / "SHA256SUMS.txt").write_bytes(internal_checksums)
        _write_archive(archive_path, package_root)

    manifest_path.write_bytes(manifest_bytes)
    external_checksums = (
        f"{_sha256(archive_path)}  {archive_path.name}\n"
        f"{_sha256(manifest_path)}  {manifest_path.name}\n"
    ).encode()
    checksums_path.write_bytes(external_checksums)
    return archive_path, manifest_path, checksums_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Assemble assessment-kit release assets")
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--created-at", required=True)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        assets = assemble_release(
            repository_root=args.repository_root.resolve(),
            version=args.version,
            source_revision=args.source_revision,
            created_at=args.created_at,
            wheel=args.wheel.resolve(),
            output_directory=args.output_directory.resolve(),
        )
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    for asset in assets:
        print(asset)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
