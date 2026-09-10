from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from skill_assessment.errors import AssessmentError
from skill_assessment.packages import discover_packages, select_packages, validate_package


def make_skill(parent: Path, name: str = "example-skill", description: str = "An example") -> Path:
    skill = parent / name
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(f"---\nname: {name}\ndescription: {description}\n---\n\n# Example\n")
    return skill


def expected_digest(skill: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(path for path in skill.rglob("*") if path.is_file()):
        digest.update(path.relative_to(skill).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def test_validate_package_uses_directory_identity_and_contract_digest(tmp_path: Path):
    skill = make_skill(tmp_path)
    (skill / "references").mkdir()
    (skill / "references" / "guide.txt").write_bytes(b"exact bytes\n")

    package = validate_package(skill)

    assert package.name == "example-skill"
    assert package.content_sha256 == expected_digest(skill)


def test_validate_package_rejects_frontmatter_name_mismatch(tmp_path: Path):
    skill = make_skill(tmp_path, name="folder-name")
    (skill / "SKILL.md").write_text("---\nname: other-name\ndescription: An example\n---\n")

    with pytest.raises(AssessmentError, match="must match package directory"):
        validate_package(skill)


def test_validate_package_rejects_symlink(tmp_path: Path):
    skill = make_skill(tmp_path)
    os.symlink(skill / "SKILL.md", skill / "copy.md")

    with pytest.raises(AssessmentError, match="symbolic link"):
        validate_package(skill)


def test_discovery_selects_outermost_skill_and_root_skill(tmp_path: Path):
    outer = make_skill(tmp_path / "group", "outer")
    make_skill(outer / "examples", "nested")

    assert discover_packages(tmp_path) == [outer]
    assert discover_packages(outer) == [outer]


def test_select_packages_rejects_duplicate_portable_names(tmp_path: Path):
    first = make_skill(tmp_path / "one", "duplicate")
    second = make_skill(tmp_path / "two", "duplicate")

    with pytest.raises(AssessmentError, match="duplicate selected skill names"):
        select_packages(skill_paths=[first, second], root=None)


def test_empty_root_is_a_valid_empty_selection(tmp_path: Path):
    assert select_packages(skill_paths=None, root=tmp_path) == []
