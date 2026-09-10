"""Assemble the prebuilt site release without building or assessing its inputs."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import shutil
import tarfile
import tempfile
from datetime import UTC, datetime
from pathlib import Path

RELEASE_MANIFEST_SCHEMA = "skill-exchange-release-manifest/v1"
SEMVER_PATTERN = re.compile(
    r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-(?:0|[1-9][0-9]*|[0-9A-Za-z-]*[A-Za-z-][0-9A-Za-z-]*)"
    r"(?:\.(?:0|[1-9][0-9]*|[0-9A-Za-z-]*[A-Za-z-][0-9A-Za-z-]*))*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
)


class ReleaseError(ValueError):
    pass


def validate_version(version: str) -> None:
    if not SEMVER_PATTERN.fullmatch(version):
        raise ReleaseError(f"version must be a SemVer value without a leading v: {version}")


def _reject_link(path: Path) -> None:
    if path.is_symlink() or path.is_junction():
        raise ReleaseError(f"release input must not contain a symbolic link or directory junction: {path}")


def _check_source_path(source: Path) -> None:
    # Do not resolve the path first: that would hide a linked source or parent.
    absolute = source.absolute()
    for parent in reversed(absolute.parents):
        _reject_link(parent)
    _reject_link(absolute)


def _tree_entries(root: Path) -> list[Path]:
    _check_source_path(root)
    if not root.is_dir():
        raise ReleaseError(f"required release directory is missing: {root}")
    entries: list[Path] = []
    pending = [root]
    while pending:
        directory = pending.pop()
        for path in sorted(directory.iterdir()):
            # Reject links before classifying or descending into the entry.
            _reject_link(path)
            if path.is_dir():
                pending.append(path)
            elif not path.is_file():
                raise ReleaseError(f"release input must be a regular file or directory: {path}")
            entries.append(path)
    return sorted(entries)


def _regular_files(root: Path) -> list[Path]:
    return [path for path in _tree_entries(root) if path.is_file()]


def _copy_tree(source: Path, destination: Path) -> None:
    """Preflight the entire source, then copy into a trusted staging directory."""
    entries = _tree_entries(source)
    destination.mkdir(parents=True, exist_ok=True)
    for path in entries:
        target = destination / path.relative_to(source)
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def _copy_file(source: Path, destination: Path) -> None:
    _check_source_path(source)
    if not source.is_file():
        raise ReleaseError(f"required release file is missing or invalid: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def _sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def _write_metadata(
    root: Path,
    files: list[Path],
    *,
    product: str,
    version: str,
    source_revision: str,
    created_at: str,
    checksum_manifest: bool = False,
) -> list[Path]:
    entries = [
        {"path": path.relative_to(root).as_posix(), "sha256": f"sha256:{_sha256(path)}"}
        for path in sorted(files, key=lambda path: path.relative_to(root).as_posix())
    ]
    manifest = {
        "schema_version": RELEASE_MANIFEST_SCHEMA,
        "product": product,
        "version": version,
        "source_revision": source_revision,
        "created_at": created_at,
        "produces": {"release_manifest": [RELEASE_MANIFEST_SCHEMA]},
        "consumes": {},
        "artifacts": entries,
    }
    manifest_path = root / "release-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    checksum_entries = list(entries)
    if checksum_manifest:
        checksum_entries.append({"path": manifest_path.name, "sha256": f"sha256:{_sha256(manifest_path)}"})
    checksum_path = root / "SHA256SUMS.txt"
    checksum_path.write_text(
        "".join(f"{entry['sha256'].removeprefix('sha256:')}  {entry['path']}\n" for entry in checksum_entries),
        encoding="utf-8",
        newline="\n",
    )
    return [manifest_path, checksum_path]


def _stage_deployment_kit(repo_root: Path, site_dir: Path, stage_root: Path) -> None:
    public = stage_root / "public"
    _copy_tree(site_dir, public)
    (public / ".gitkeep").unlink(missing_ok=True)
    if not (public / "index.html").is_file():
        raise ReleaseError("prebuilt site must contain public/index.html")
    for name in ("assets", "downloads"):
        if not (public / name).is_dir():
            raise ReleaseError(f"prebuilt site must contain public/{name}")

    product = repo_root / "products" / "deployment-kit"
    docs = product / "docs" / "prebuilt"
    _copy_file(product / "ci" / "gitlab" / "prebuilt" / ".gitlab-ci.yml", stage_root / ".gitlab-ci.yml")
    _copy_file(docs / "README.md", stage_root / "README.md")
    for name in ("install.md", "deploy-gitlab-pages.md", "deploy-static-hosting.md"):
        _copy_file(docs / name, stage_root / "docs" / name)
    schema = Path("contracts/release-manifest/v1/release-manifest.schema.json")
    _copy_file(repo_root / schema, stage_root / schema)
    _copy_file(product / "scripts" / "verify_prebuilt.py", stage_root / "scripts" / "verify_prebuilt.py")


def _write_tar_gz(source: Path, destination: Path, *, source_date_epoch: int) -> None:
    def normalize(info: tarfile.TarInfo) -> tarfile.TarInfo:
        if not (info.isfile() or info.isdir()):
            raise ReleaseError(f"release archive must contain only regular files and directories: {info.name}")
        info.uid = info.gid = 0
        info.uname = info.gname = "root"
        info.mtime = source_date_epoch
        return info

    with destination.open("wb") as raw_handle:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw_handle, mtime=source_date_epoch) as gzip_handle:
            with tarfile.open(fileobj=gzip_handle, mode="w") as archive:
                archive.add(source, arcname=source.name, recursive=True, filter=normalize)


def build_release(
    *,
    repo_root: Path,
    site_dir: Path,
    output_dir: Path,
    version: str,
    source_revision: str,
    source_date_epoch: int | None = None,
) -> list[Path]:
    """Build only the prebuilt archive and its external manifest/checksum files."""
    validate_version(version)
    if not source_revision.strip():
        raise ReleaseError("source revision must not be empty")
    _check_source_path(repo_root)
    epoch = source_date_epoch if source_date_epoch is not None else int(datetime.now(UTC).timestamp())
    timestamp = datetime.fromtimestamp(epoch, UTC).isoformat().replace("+00:00", "Z")
    product = "deployment-kit-prebuilt"
    archive_path = output_dir / f"{product}-{version}.tar.gz"

    with tempfile.TemporaryDirectory(prefix="sklc-prebuilt-") as temporary:
        package_root = Path(temporary) / f"{product}-{version}"
        _stage_deployment_kit(repo_root, site_dir, package_root)
        # Enumerate before writing root metadata; nested files with the same names
        # are ordinary assets and must remain covered by the checksums.
        _write_metadata(
            package_root, _regular_files(package_root), product=product, version=version,
            source_revision=source_revision, created_at=timestamp,
        )
        # Invalid sources must fail before any release assets are published here.
        output_dir.mkdir(parents=True, exist_ok=True)
        _write_tar_gz(package_root, archive_path, source_date_epoch=epoch)

    metadata_paths = _write_metadata(
        output_dir, [archive_path], product="sklc", version=version,
        source_revision=source_revision, created_at=timestamp, checksum_manifest=True,
    )
    return [archive_path, *metadata_paths]


def extract_release_notes(notes_path: Path, version: str) -> str:
    """Select exactly one nonempty version section, ignoring fenced examples."""
    validate_version(version)
    _check_source_path(notes_path)
    if not notes_path.is_file():
        raise ReleaseError(f"release notes file is missing: {notes_path}")
    lines = notes_path.read_text(encoding="utf-8").splitlines()
    headings: list[tuple[int, str, str]] = []
    fence: str | None = None
    for index, line in enumerate(lines):
        if fence is not None:
            if re.fullmatch(rf" {{0,3}}{fence[0]}{{{len(fence)},}}[ \t]*", line):
                fence = None
            continue
        opening = re.match(r" {0,3}(`{3,}|~{3,})", line)
        if opening:
            fence = opening[1]
            continue
        heading = re.fullmatch(r" {0,3}(#{1,2})[ \t]+(.+?)[ \t]*", line)
        if heading:
            headings.append((index, heading[1], heading[2]))
    matches = [index for index, level, title in headings if level == "##" and title == version]
    if len(matches) != 1:
        raise ReleaseError(f"release notes must contain exactly one heading '## {version}'")
    start = matches[0]
    end = next((index for index, _level, _title in headings if index > start), len(lines))
    if not "\n".join(lines[start + 1:end]).strip():
        raise ReleaseError(f"release notes section for {version} is empty")
    return "\n".join(lines[start:end]).strip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Assemble the prebuilt site release package")
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build", help="package an already-built site; do not build or assess inputs")
    build.add_argument("--version", required=True)
    build.add_argument("--source-revision", required=True)
    build.add_argument("--repo-root", type=Path, default=Path.cwd())
    build.add_argument("--site-dir", type=Path, default=Path("site/dist"))
    build.add_argument("--output-dir", type=Path, default=Path("release"))
    validate = commands.add_parser("validate-version", help="validate a SemVer release version without a leading v")
    validate.add_argument("--version", required=True)
    notes = commands.add_parser("release-notes", help="extract one accepted version section")
    notes.add_argument("--version", required=True)
    notes.add_argument("--notes-file", type=Path, default=Path("RELEASE_NOTES.md"))
    notes.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "validate-version":
        validate_version(args.version)
        return
    if args.command == "release-notes":
        snippet = extract_release_notes(args.notes_file, args.version)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(snippet, encoding="utf-8", newline="\n")
        return
    source_date_epoch = int(os.environ["SOURCE_DATE_EPOCH"]) if "SOURCE_DATE_EPOCH" in os.environ else None
    # Keep source links visible to the safety checks, including relative CLI inputs.
    repo_root = args.repo_root.absolute()
    site_dir = args.site_dir if args.site_dir.is_absolute() else repo_root / args.site_dir
    built = build_release(
        repo_root=repo_root,
        site_dir=site_dir,
        output_dir=args.output_dir.absolute(),
        version=args.version,
        source_revision=args.source_revision,
        source_date_epoch=source_date_epoch,
    )
    print(json.dumps({"artifacts": [str(path) for path in built]}, indent=2))


if __name__ == "__main__":
    main()
