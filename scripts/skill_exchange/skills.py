from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .frontmatter import parse_frontmatter
from .models import SkillMetadata, SkillPackage

MAX_SKILL_FILES = 500
MAX_SKILL_FILE_BYTES = 5 * 1024 * 1024


def discover_skills(skills_root: Path) -> list[SkillPackage]:
    if not skills_root.exists():
        return []

    packages: list[SkillPackage] = []
    for skill_file in sorted(skills_root.glob("*/*/SKILL.md")):
        skill_dir = skill_file.parent
        namespace = skill_dir.parent.name
        skill_id = skill_dir.name
        frontmatter, _body = parse_frontmatter(skill_file.read_text())
        metadata = _metadata_from_frontmatter(namespace, skill_id, frontmatter)
        packages.append(
            SkillPackage(
                metadata=metadata,
                path=skill_dir,
                skill_file=skill_file,
                content_hash=hash_skill_package(skill_dir),
            )
        )
    return packages


def hash_skill_package(skill_dir: Path) -> str:
    digest = hashlib.sha256()
    for path in package_files(skill_dir):
        rel = path.relative_to(skill_dir).as_posix()
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def package_files(skill_dir: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(skill_dir.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"skill package must not contain symlink: {path.relative_to(skill_dir).as_posix()}")
        if not path.is_file():
            continue
        if path.stat().st_size > MAX_SKILL_FILE_BYTES:
            raise ValueError(f"skill package file is too large: {path.relative_to(skill_dir).as_posix()}")
        files.append(path)
        if len(files) > MAX_SKILL_FILES:
            raise ValueError(f"skill package contains more than {MAX_SKILL_FILES} files")
    return files


def _metadata_from_frontmatter(namespace: str, skill_id: str, frontmatter: dict[str, Any]) -> SkillMetadata:
    metadata = frontmatter.get("metadata") or {}
    raw_tags = metadata.get("ai4sdlc.tags") or ""
    if isinstance(raw_tags, str):
        tags = tuple(tag.strip() for tag in raw_tags.split(",") if tag.strip())
    elif isinstance(raw_tags, list):
        tags = tuple(str(tag).strip() for tag in raw_tags if str(tag).strip())
    else:
        tags = ()

    return SkillMetadata(
        namespace=namespace,
        skill_id=skill_id,
        name=str(frontmatter.get("name") or ""),
        description=str(frontmatter.get("description") or ""),
        category=metadata.get("ai4sdlc.category"),
        tags=tags,
        owner=metadata.get("ai4sdlc.owner"),
        upstream_url=metadata.get("ai4sdlc.upstream_url"),
        raw=frontmatter,
    )
