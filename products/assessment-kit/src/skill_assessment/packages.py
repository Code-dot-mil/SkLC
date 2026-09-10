from __future__ import annotations

import hashlib
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .errors import AssessmentError

MAX_PACKAGE_FILES = 500
MAX_FILE_BYTES = 5 * 1024 * 1024
SKILL_NAME_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62})$")


@dataclass(frozen=True)
class SkillPackage:
    name: str
    path: Path
    metadata: dict[str, Any]
    content_sha256: str


def parse_frontmatter(raw: bytes) -> dict[str, Any]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AssessmentError("SKILL.md must be valid UTF-8") from exc
    if not text.startswith("---\n"):
        raise AssessmentError("SKILL.md must start with YAML frontmatter")
    marker = "\n---\n"
    end = text.find(marker, 4)
    if end < 0:
        raise AssessmentError("SKILL.md frontmatter closing marker not found")
    try:
        parsed = yaml.safe_load(text[4:end]) or {}
    except yaml.YAMLError as exc:
        raise AssessmentError(f"SKILL.md frontmatter is invalid YAML: {exc}") from exc
    if not isinstance(parsed, dict):
        raise AssessmentError("SKILL.md frontmatter must parse to a mapping")
    return parsed


def _validate_metadata(metadata: dict[str, Any], expected_name: str) -> None:
    allowed_name = metadata.get("name")
    if not isinstance(allowed_name, str) or not SKILL_NAME_RE.fullmatch(allowed_name):
        raise AssessmentError("SKILL.md frontmatter name does not satisfy skill-package/v1")
    if allowed_name != expected_name:
        raise AssessmentError(
            f"SKILL.md name must match package directory: expected {expected_name}, got {allowed_name}"
        )
    description = metadata.get("description")
    if not isinstance(description, str) or not description.strip():
        raise AssessmentError("SKILL.md frontmatter description must be a non-blank string")
    extended = metadata.get("metadata")
    if extended is None:
        return
    if not isinstance(extended, dict):
        raise AssessmentError("SKILL.md frontmatter metadata must be a mapping")
    for key in (
        "ai4sdlc.namespace",
        "ai4sdlc.category",
        "ai4sdlc.owner",
        "ai4sdlc.upstream_url",
    ):
        value = extended.get(key)
        if value is not None and (not isinstance(value, str) or not value):
            raise AssessmentError(f"SKILL.md frontmatter metadata.{key} must be a non-empty string")
    tags = extended.get("ai4sdlc.tags")
    if tags is not None:
        if isinstance(tags, str):
            return
        if not isinstance(tags, list) or any(not isinstance(tag, str) or not tag for tag in tags):
            raise AssessmentError("SKILL.md frontmatter metadata.ai4sdlc.tags must be a string or non-empty strings")
        if len(tags) != len(set(tags)):
            raise AssessmentError("SKILL.md frontmatter metadata.ai4sdlc.tags must contain unique values")


def package_files(skill_dir: Path) -> list[Path]:
    try:
        root_stat = skill_dir.lstat()
    except OSError as exc:
        raise AssessmentError(f"cannot read skill package {skill_dir}: {exc}") from exc
    if stat.S_ISLNK(root_stat.st_mode):
        raise AssessmentError(f"skill package must not be a symbolic link: {skill_dir}")
    if not stat.S_ISDIR(root_stat.st_mode):
        raise AssessmentError(f"skill package is not a directory: {skill_dir}")

    root = skill_dir.resolve()
    files: list[Path] = []
    walk_error: OSError | None = None

    def record_walk_error(error: OSError) -> None:
        nonlocal walk_error
        walk_error = error

    for current, dir_names, file_names in os.walk(
        skill_dir, topdown=True, followlinks=False, onerror=record_walk_error
    ):
        if walk_error is not None:
            raise AssessmentError(f"cannot read skill package {skill_dir}: {walk_error}") from walk_error
        dir_names.sort()
        file_names.sort()
        current_path = Path(current)
        for name in [*dir_names, *file_names]:
            path = current_path / name
            try:
                entry_stat = path.lstat()
            except OSError as exc:
                raise AssessmentError(f"cannot read package entry {path}: {exc}") from exc
            relative = path.relative_to(skill_dir).as_posix()
            if stat.S_ISLNK(entry_stat.st_mode):
                raise AssessmentError(f"skill package must not contain symbolic link: {relative}")
            try:
                path.resolve().relative_to(root)
            except (OSError, ValueError) as exc:
                raise AssessmentError(f"skill package path escapes package directory: {relative}") from exc
            if name in dir_names:
                if not stat.S_ISDIR(entry_stat.st_mode):
                    raise AssessmentError(f"unsupported package filesystem object: {relative}")
                continue
            if not stat.S_ISREG(entry_stat.st_mode):
                raise AssessmentError(f"unsupported package filesystem object: {relative}")
            if entry_stat.st_size > MAX_FILE_BYTES:
                raise AssessmentError(f"skill package file exceeds 5 MiB: {relative}")
            files.append(path)
            if len(files) > MAX_PACKAGE_FILES:
                raise AssessmentError(f"skill package contains more than {MAX_PACKAGE_FILES} files")
    if walk_error is not None:
        raise AssessmentError(f"cannot read skill package {skill_dir}: {walk_error}") from walk_error
    return sorted(files, key=lambda path: path.relative_to(skill_dir).as_posix())


def hash_package(skill_dir: Path, files: list[Path] | None = None) -> str:
    digest = hashlib.sha256()
    for path in files if files is not None else package_files(skill_dir):
        digest.update(path.relative_to(skill_dir).as_posix().encode("utf-8"))
        digest.update(b"\0")
        try:
            digest.update(path.read_bytes())
        except OSError as exc:
            raise AssessmentError(f"cannot read package file {path}: {exc}") from exc
        digest.update(b"\0")
    return digest.hexdigest()


def validate_package(path: Path) -> SkillPackage:
    path = path.expanduser()
    files = package_files(path)
    skill_file = path / "SKILL.md"
    if skill_file not in files:
        raise AssessmentError(f"skill package is missing SKILL.md: {path}")
    name = path.name
    if not SKILL_NAME_RE.fullmatch(name):
        raise AssessmentError(f"package directory name does not satisfy skill-package/v1: {name}")
    try:
        metadata = parse_frontmatter(skill_file.read_bytes())
    except OSError as exc:
        raise AssessmentError(f"cannot read {skill_file}: {exc}") from exc
    _validate_metadata(metadata, name)
    return SkillPackage(name=name, path=path.resolve(), metadata=metadata, content_sha256=hash_package(path, files))


def discover_packages(root: Path) -> list[Path]:
    root = root.expanduser()
    if root.is_symlink():
        raise AssessmentError(f"selection root must not be a symbolic link: {root}")
    if not root.exists():
        raise AssessmentError(f"selection root does not exist: {root}")
    if not root.is_dir():
        raise AssessmentError(f"selection root is not a directory: {root}")

    selected: list[Path] = []
    for current, dir_names, file_names in os.walk(root, topdown=True, followlinks=False):
        dir_names[:] = sorted(name for name in dir_names if not (Path(current) / name).is_symlink())
        if "SKILL.md" in file_names:
            selected.append(Path(current))
            dir_names.clear()
    return selected


def select_packages(*, skill_paths: list[Path] | None, root: Path | None) -> list[SkillPackage]:
    if bool(skill_paths) == (root is not None):
        raise AssessmentError("select exactly one mode: one or more --skill arguments, or --root")
    paths = skill_paths if skill_paths else discover_packages(root)  # type: ignore[arg-type]
    packages = [validate_package(path) for path in paths]
    seen: set[str] = set()
    duplicates: set[str] = set()
    for package in packages:
        if package.name in seen:
            duplicates.add(package.name)
        seen.add(package.name)
    if duplicates:
        raise AssessmentError(f"duplicate selected skill names: {', '.join(sorted(duplicates))}")
    return sorted(packages, key=lambda package: package.name)


def reject_output_overlap(output: Path, packages: list[SkillPackage]) -> None:
    resolved = output.expanduser().resolve()
    for package in packages:
        try:
            resolved.relative_to(package.path)
        except ValueError:
            continue
        raise AssessmentError(f"output directory must not be inside skill package {package.name}: {output}")
