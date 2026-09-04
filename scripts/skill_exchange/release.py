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

import yaml

from .frontmatter import parse_frontmatter

RELEASE_MANIFEST_SCHEMA = "skill-exchange-release-manifest/v1"
CATALOG_POLICY_SCHEMA = "skill-exchange-catalog-policy/v1"
SEMVER_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")
SKILL_NAME_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62})$")
DOWNLOAD_REFERENCE_PATTERN = re.compile(r"(?:href|src)=[\"'](downloads/[^\"'?#]+)|[\"'](downloads/[^\"'?#]+)[\"']")
ROOT_DOWNLOAD_REFERENCE_PATTERN = re.compile(r"(?:href|src)=[\"']/downloads/|[\"']/downloads/")


class ReleaseError(ValueError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _regular_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ReleaseError(f"release input must not contain a symbolic link: {path}")
        if path.is_file():
            files.append(path)
    return files


def _copy_tree(source: Path, destination: Path) -> None:
    if not source.is_dir():
        raise ReleaseError(f"required release directory is missing: {source}")
    destination.mkdir(parents=True, exist_ok=True)
    for directory in sorted(path for path in source.rglob("*") if path.is_dir()):
        if directory.is_symlink():
            raise ReleaseError(f"release input must not contain a symbolic link: {directory}")
        (destination / directory.relative_to(source)).mkdir(parents=True, exist_ok=True)
    for path in _regular_files(source):
        relative = path.relative_to(source)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def _copy_file(source: Path, destination: Path) -> None:
    if source.is_symlink() or not source.is_file():
        raise ReleaseError(f"required release file is missing or invalid: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def _created_at(source_date_epoch: int | None) -> str:
    if source_date_epoch is None:
        return datetime.now(UTC).isoformat().replace("+00:00", "Z")
    return datetime.fromtimestamp(source_date_epoch, UTC).isoformat().replace("+00:00", "Z")


def _write_product_metadata(
    root: Path,
    *,
    product: str,
    version: str,
    source_revision: str,
    created_at: str,
    produces: dict[str, list[str]],
    consumes: dict[str, list[str]],
) -> None:
    entries = [
        {
            "path": path.relative_to(root).as_posix(),
            "sha256": f"sha256:{_sha256(path)}",
        }
        for path in _regular_files(root)
        if path.name not in {"release-manifest.json", "SHA256SUMS.txt"}
    ]
    if not entries:
        raise ReleaseError(f"release package has no files: {root}")

    manifest = {
        "schema_version": RELEASE_MANIFEST_SCHEMA,
        "product": product,
        "version": version,
        "source_revision": source_revision,
        "created_at": created_at,
        "produces": produces,
        "consumes": consumes,
        "artifacts": entries,
    }
    (root / "release-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (root / "SHA256SUMS.txt").write_text(
        "".join(f"{entry['sha256'].removeprefix('sha256:')}  {entry['path']}\n" for entry in entries),
        encoding="utf-8",
    )


def _tar_filter(info: tarfile.TarInfo, *, mtime: int) -> tarfile.TarInfo:
    info.uid = 0
    info.gid = 0
    info.uname = "root"
    info.gname = "root"
    info.mtime = mtime
    return info


def _write_tar_gz(source: Path, destination: Path, *, source_date_epoch: int) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as raw_handle:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw_handle, mtime=source_date_epoch) as gzip_handle:
            with tarfile.open(fileobj=gzip_handle, mode="w") as archive:
                archive.add(
                    source,
                    arcname=source.name,
                    recursive=True,
                    filter=lambda info: _tar_filter(info, mtime=source_date_epoch),
                )


def _load_catalog_policy(path: Path) -> list[str]:
    if not path.is_file():
        raise ReleaseError(f"catalog policy is missing: {path}")
    policy = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(policy, dict) or set(policy) != {"schema_version", "mode", "skills"}:
        raise ReleaseError("catalog policy must contain exactly schema_version, mode, and skills")
    if policy["schema_version"] != CATALOG_POLICY_SCHEMA:
        raise ReleaseError("catalog policy has an unsupported schema_version")
    if policy["mode"] not in {"include-list", "exclude-list"}:
        raise ReleaseError("catalog policy mode must be include-list or exclude-list")
    skills = policy["skills"]
    valid_skills = isinstance(skills, list) and all(
        isinstance(skill, str) and SKILL_NAME_PATTERN.fullmatch(skill) for skill in skills
    )
    if not valid_skills:
        raise ReleaseError("catalog policy skills must be valid skill names")
    if len(skills) != len(set(skills)):
        raise ReleaseError("catalog policy contains duplicate skill names")
    return skills


def _selected_skills(repo_root: Path, policy_path: Path) -> list[str]:
    listed = _load_catalog_policy(policy_path)
    policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    source_root = repo_root / "skills" / "ai4sdlc"
    if not source_root.is_dir():
        raise ReleaseError(f"catalog skill source is missing: {source_root}")
    available = sorted(path.name for path in source_root.iterdir() if path.is_dir() and (path / "SKILL.md").is_file())
    unknown = sorted(set(listed) - set(available))
    if unknown:
        raise ReleaseError(f"catalog policy names unknown skills: {', '.join(unknown)}")
    if policy["mode"] == "include-list":
        return sorted(listed)
    return sorted(set(available) - set(listed))


def _validate_skill(source: Path, expected_name: str) -> None:
    frontmatter, _ = parse_frontmatter((source / "SKILL.md").read_text(encoding="utf-8"))
    if frontmatter.get("name") != expected_name:
        raise ReleaseError(f"skill frontmatter name does not match its directory: {expected_name}")
    if not isinstance(frontmatter.get("description"), str) or not frontmatter["description"].strip():
        raise ReleaseError(f"skill frontmatter description is missing: {expected_name}")


def _validate_download_references(public_root: Path) -> None:
    downloads_root = (public_root / "downloads").resolve()
    if not downloads_root.is_dir():
        raise ReleaseError("prebuilt site must contain public/downloads")
    for path in _regular_files(public_root):
        if path.suffix.lower() not in {".html", ".json", ".js"}:
            continue
        text = path.read_text(encoding="utf-8")
        if ROOT_DOWNLOAD_REFERENCE_PATTERN.search(text):
            raise ReleaseError(f"site download references must be relative: {path.relative_to(public_root).as_posix()}")
        for match in DOWNLOAD_REFERENCE_PATTERN.finditer(text):
            reference = match.group(1) or match.group(2)
            relative = Path(reference.removeprefix("downloads/"))
            target = (downloads_root / relative).resolve()
            if downloads_root not in target.parents or not target.is_file():
                raise ReleaseError(f"site references a missing or unsafe download: {reference}")


def _stage_deployment_kit(repo_root: Path, site_dir: Path, stage_root: Path) -> None:
    docs_source = repo_root / "products" / "deployment-kit" / "docs" / "prebuilt"
    _copy_file(
        repo_root / "products" / "deployment-kit" / "ci" / "gitlab" / "prebuilt" / ".gitlab-ci.yml",
        stage_root / ".gitlab-ci.yml",
    )
    _copy_file(docs_source / "README.md", stage_root / "README.md")
    _copy_file(docs_source / "install.md", stage_root / "docs" / "install.md")
    _copy_file(docs_source / "deploy-gitlab-pages.md", stage_root / "docs" / "deploy-gitlab-pages.md")
    _copy_file(docs_source / "deploy-static-hosting.md", stage_root / "docs" / "deploy-static-hosting.md")
    _copy_tree(
        repo_root / "contracts" / "release-manifest" / "v1",
        stage_root / "contracts" / "release-manifest" / "v1",
    )
    _copy_tree(site_dir, stage_root / "public")
    (stage_root / "public" / ".gitkeep").unlink(missing_ok=True)
    if not (stage_root / "public" / "index.html").is_file():
        raise ReleaseError("prebuilt site must contain public/index.html")
    if not (stage_root / "public" / "assets").is_dir():
        raise ReleaseError("prebuilt site must contain public/assets")
    _validate_download_references(stage_root / "public")


def _stage_skill_catalog(repo_root: Path, stage_root: Path) -> None:
    product_root = repo_root / "products" / "skill-catalog"
    _copy_file(product_root / "README.md", stage_root / "README.md")
    policy_path = product_root / "catalog-policy.yaml"
    selected = _selected_skills(repo_root, policy_path)
    if not selected:
        raise ReleaseError("catalog policy selected no skills")
    for skill_name in selected:
        source = repo_root / "skills" / "ai4sdlc" / skill_name
        _validate_skill(source, skill_name)
        _copy_tree(source, stage_root / "skills" / skill_name)
    _copy_tree(repo_root / "contracts" / "skill-package" / "v1", stage_root / "contracts" / "skill-package" / "v1")
    _copy_tree(
        repo_root / "contracts" / "release-manifest" / "v1",
        stage_root / "contracts" / "release-manifest" / "v1",
    )


def build_release(
    *,
    repo_root: Path,
    site_dir: Path,
    output_dir: Path,
    version: str,
    source_revision: str,
    source_date_epoch: int | None = None,
) -> list[Path]:
    if not SEMVER_PATTERN.fullmatch(version):
        raise ReleaseError(f"version must be a SemVer value without a leading v: {version}")
    if not source_revision:
        raise ReleaseError("source revision must not be empty")
    epoch = source_date_epoch if source_date_epoch is not None else int(datetime.now(UTC).timestamp())
    timestamp = _created_at(epoch)
    output_dir.mkdir(parents=True, exist_ok=True)

    archives: list[Path] = []
    with tempfile.TemporaryDirectory(prefix="sklc-release-") as temporary:
        temporary_root = Path(temporary)
        products = (
            (
                "deployment-kit-prebuilt",
                lambda root: _stage_deployment_kit(repo_root, site_dir, root),
                {"deployment-kit-prebuilt": [version]},
                {"release-manifest": ["v1"]},
            ),
            (
                "skill-catalog",
                lambda root: _stage_skill_catalog(repo_root, root),
                {"skill-catalog": [version]},
                {"skill-package": ["v1"], "release-manifest": ["v1"]},
            ),
        )
        for product, stage, produces, consumes in products:
            package_root = temporary_root / f"{product}-{version}"
            package_root.mkdir()
            stage(package_root)
            _write_product_metadata(
                package_root,
                product=product,
                version=version,
                source_revision=source_revision,
                created_at=timestamp,
                produces=produces,
                consumes=consumes,
            )
            archive = output_dir / f"{product}-{version}.tar.gz"
            _write_tar_gz(package_root, archive, source_date_epoch=epoch)
            archives.append(archive)

    external_entries = [
        {"path": archive.name, "sha256": f"sha256:{_sha256(archive)}"}
        for archive in archives
    ]
    external_manifest = {
        "schema_version": RELEASE_MANIFEST_SCHEMA,
        "product": "sklc",
        "version": version,
        "source_revision": source_revision,
        "created_at": timestamp,
        "produces": {
            "deployment-kit-prebuilt": [version],
            "skill-catalog": [version],
        },
        "consumes": {},
        "artifacts": external_entries,
    }
    manifest_path = output_dir / "release-manifest.json"
    manifest_path.write_text(json.dumps(external_manifest, indent=2) + "\n", encoding="utf-8")
    checksum_entries = [*external_entries, {"path": manifest_path.name, "sha256": f"sha256:{_sha256(manifest_path)}"}]
    checksum_path = output_dir / "SHA256SUMS.txt"
    checksum_path.write_text(
        "".join(f"{entry['sha256'].removeprefix('sha256:')}  {entry['path']}\n" for entry in checksum_entries),
        encoding="utf-8",
    )
    return [*archives, manifest_path, checksum_path]


def extract_release_notes(notes_path: Path, version: str) -> str:
    if not notes_path.is_file():
        raise ReleaseError(f"release notes file is missing: {notes_path}")
    lines = notes_path.read_text(encoding="utf-8").splitlines()
    heading = f"## {version}"
    try:
        start = lines.index(heading)
    except ValueError as error:
        raise ReleaseError(f"release notes do not contain the heading {heading!r}") from error
    end = next((index for index in range(start + 1, len(lines)) if lines[index].startswith("## ")), len(lines))
    snippet = "\n".join(lines[start:end]).strip()
    if snippet == heading:
        raise ReleaseError(f"release notes section for {version} is empty")
    return snippet + "\n"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build and verify SkLC release artifacts")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build", help="build the currently releasable product artifacts")
    build.add_argument("--version", required=True)
    build.add_argument("--source-revision", required=True)
    build.add_argument("--repo-root", type=Path, default=Path.cwd())
    build.add_argument("--site-dir", type=Path, default=Path("site/dist"))
    build.add_argument("--output-dir", type=Path, default=Path("release"))

    notes = subparsers.add_parser("release-notes", help="extract one accepted version section")
    notes.add_argument("--version", required=True)
    notes.add_argument("--notes-file", type=Path, default=Path("RELEASE_NOTES.md"))
    notes.add_argument("--output", type=Path, required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.command == "build":
        source_date_epoch = int(os.environ["SOURCE_DATE_EPOCH"]) if "SOURCE_DATE_EPOCH" in os.environ else None
        built = build_release(
            repo_root=args.repo_root.resolve(),
            site_dir=(args.repo_root / args.site_dir).resolve() if not args.site_dir.is_absolute() else args.site_dir,
            output_dir=args.output_dir.resolve(),
            version=args.version,
            source_revision=args.source_revision,
            source_date_epoch=source_date_epoch,
        )
        print(json.dumps({"artifacts": [str(path) for path in built]}, indent=2))
        return

    snippet = extract_release_notes(args.notes_file, args.version)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(snippet, encoding="utf-8")


if __name__ == "__main__":
    main()
