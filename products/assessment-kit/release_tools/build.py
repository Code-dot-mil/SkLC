from __future__ import annotations

import argparse
import re
import sys
import tempfile
import zipfile
from collections.abc import Sequence
from datetime import datetime
from email.parser import BytesParser
from pathlib import Path

from packaging.version import InvalidVersion, Version
from skill_exchange.release import copy_release_file, copy_release_tree, validate_version, write_release_assets

PRODUCT = "assessment-kit"
PACKAGE_DISTRIBUTION = "skill_assessment"
CONTRACT_PATHS = (
    Path("skill-package/v1"),
    Path("boe/v1"),
    Path("assessment-artifacts/v1"),
    Path("release-manifest/v1"),
)

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
    validate_version(version)
    if not re.fullmatch(r"[a-f0-9]{40}", source_revision):
        raise ValueError("source revision must be a full lowercase 40-character Git commit")
    if not re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}[Tt][0-9]{2}:[0-9]{2}:[0-9]{2}"
        r"(?:\.[0-9]+)?(?:[Zz]|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])", created_at
    ):
        raise ValueError("created-at must be an RFC 3339 date-time")
    try:
        parsed_created_at = datetime.fromisoformat(created_at.upper().replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("created-at must be an ISO 8601 date-time with timezone") from exc
    if parsed_created_at.tzinfo is None:
        raise ValueError("created-at must include a timezone")
    if not wheel.is_file() or wheel.is_symlink():
        raise ValueError("wheel must be a regular file")
    wheel_version = _wheel_version(wheel)
    try:
        expected_version = Version(version)
        actual_version = Version(wheel_version)
    except InvalidVersion as exc:
        raise ValueError("release and wheel versions must be representable as Python versions") from exc
    if "-" in version.split("+", 1)[0] and (not expected_version.is_prerelease or expected_version.post is not None):
        raise ValueError("SemVer prerelease must map to a Python prerelease, not a post-release")
    if actual_version != expected_version:
        raise ValueError(f"wheel version {wheel_version} does not match release version {version}")
    return wheel_version


def assemble_release(
    *,
    repository_root: Path,
    version: str,
    source_revision: str,
    created_at: str,
    wheel: Path,
    output_directory: Path,
) -> list[Path]:
    wheel_version = _validate_inputs(version, source_revision, created_at, wheel)
    product_root = repository_root / "products" / "assessment-kit"
    contracts_root = repository_root / "contracts"
    archive_path = output_directory / f"{PRODUCT}-{version}.tar.gz"
    manifest_path = output_directory / f"{PRODUCT}-{version}.release-manifest.json"
    checksums_path = output_directory / f"{PRODUCT}-{version}.SHA256SUMS.txt"
    existing = [path.name for path in (archive_path, manifest_path, checksums_path) if path.exists()]
    if existing:
        raise ValueError(f"refusing to overwrite release assets: {', '.join(existing)}")

    with tempfile.TemporaryDirectory(prefix="assessment-kit-release-") as temporary:
        package_root = Path(temporary).resolve() / f"{PRODUCT}-{version}"
        copy_release_file(product_root / "README.md", package_root / "README.md")
        copy_release_tree(product_root / "docs", package_root / "docs")
        copy_release_file(wheel, package_root / "dist" / wheel.name)
        for relative in CONTRACT_PATHS:
            copy_release_tree(contracts_root / relative, package_root / "contracts" / relative)

        manifest = {
            "product": PRODUCT,
            "version": version,
            "source_revision": source_revision,
            "created_at": created_at,
            "produces": {
                "assessment_artifacts": ["skill-exchange-assessment-artifacts/v1"],
                "boe": ["skill-exchange-boe/v1"],
            },
            "consumes": {"skill_package": ["urn:skill-exchange:skill-package:v1"]},
            "components": {
                "skill-assessment": wheel_version,
                "skillspector": "2.10.0@e29b16d305b0e738e3d4b952ba102f5522a6f084",
            },
        }
        return write_release_assets(package_root, output_directory, manifest)


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
