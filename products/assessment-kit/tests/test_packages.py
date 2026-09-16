from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from skill_assessment.errors import AssessmentError
from skill_assessment.packages import discover_packages, select_packages, validate_package


def test_validate_package_uses_directory_identity_and_contract_digest(tmp_path: Path, make_skill):
    skill = make_skill(tmp_path)
    (skill / "references").mkdir()
    (skill / "references" / "guide.txt").write_bytes(b"exact bytes\n")

    package = validate_package(skill)

    assert package.name == "example-skill"
    assert package.content_sha256 == hashlib.sha256(
        b"SKILL.md\0" + (skill / "SKILL.md").read_bytes() + b"\0references/guide.txt\0exact bytes\n\0"
    ).hexdigest()


def test_validate_package_rejects_frontmatter_name_mismatch(tmp_path: Path, make_skill):
    skill = make_skill(tmp_path, name="folder-name")
    (skill / "SKILL.md").write_text("---\nname: other-name\ndescription: An example\n---\n")

    with pytest.raises(AssessmentError, match="must match package directory"):
        validate_package(skill)


def test_validate_package_rejects_symlink(tmp_path: Path, make_skill):
    skill = make_skill(tmp_path)
    os.symlink(skill / "SKILL.md", skill / "copy.md")

    with pytest.raises(AssessmentError, match="symbolic link"):
        validate_package(skill)


def test_discovery_selects_outermost_skill_and_root_skill(tmp_path: Path, make_skill):
    outer = make_skill(tmp_path / "group", "outer")
    make_skill(outer / "examples", "nested")

    assert discover_packages(tmp_path) == [outer]
    assert discover_packages(outer) == [outer]


def test_select_packages_rejects_duplicate_portable_names(tmp_path: Path, make_skill):
    first = make_skill(tmp_path / "one", "duplicate")
    second = make_skill(tmp_path / "two", "duplicate")

    with pytest.raises(AssessmentError, match="duplicate selected skill names"):
        select_packages(skill_paths=[first, second], root=None)


def test_empty_root_is_a_valid_empty_selection(tmp_path: Path):
    assert select_packages(skill_paths=None, root=tmp_path) == []


@pytest.mark.parametrize("selection", [".", "../example-skill"])
def test_relative_selection_uses_resolved_directory_name(tmp_path, monkeypatch, selection, make_skill):
    skill = make_skill(tmp_path)
    monkeypatch.chdir(skill)

    assert validate_package(Path(selection)).name == "example-skill"
    assert select_packages(skill_paths=None, root=Path(selection))[0].path == skill


@pytest.mark.parametrize("extra", [
    "metadata: null", "metadata:\n  ai4sdlc.tags: null",
    "metadata:\n  ai4sdlc.owner: null", "metadata:\n  ai4sdlc.namespace: null",
    "metadata:\n  ai4sdlc.category: null", "metadata:\n  ai4sdlc.upstream_url: null",
])
def test_null_metadata_fails_contract_validation(tmp_path, extra, make_skill):
    skill = make_skill(tmp_path)
    (skill / "SKILL.md").write_text(
        f"---\nname: example-skill\ndescription: Test\n{extra}\n---\n"
    )
    with pytest.raises(AssessmentError, match="metadata"):
        validate_package(skill)


@pytest.mark.parametrize("nested", [False, True])
def test_unreadable_discovery_fails_instead_of_skipping_packages(tmp_path, nested, make_skill):
    root = tmp_path / "selection"
    root.mkdir()
    blocked = root / "blocked" if nested else root
    if nested:
        blocked.mkdir()
        make_skill(root)
    make_skill(blocked, "hidden")
    blocked.chmod(0)
    try:
        if os.access(blocked, os.R_OK):
            pytest.skip("test requires filesystem permission enforcement")
        with pytest.raises(AssessmentError, match="cannot read selection"):
            select_packages(skill_paths=None, root=root)
    finally:
        blocked.chmod(0o700)


@pytest.mark.parametrize("newline,terminal_newline", [("\r\n", True), ("\n", False)])
def test_frontmatter_line_endings_preserve_package_bytes(tmp_path, newline, terminal_newline, make_skill):
    skill = make_skill(tmp_path)
    content = newline.join(["---", "name: example-skill", "description: Test", "---"])
    if terminal_newline:
        content += newline
    (skill / "SKILL.md").write_bytes(content.encode())
    expected = hashlib.sha256(b"SKILL.md\0" + content.encode() + b"\0").hexdigest()
    assert validate_package(skill).content_sha256 == expected


@pytest.mark.parametrize("limit", ["file-size", "file-count"])
def test_package_limits_fail_before_hashing(tmp_path, limit, make_skill):
    skill = make_skill(tmp_path)
    if limit == "file-size":
        with (skill / "large").open("wb") as handle:
            handle.truncate(5 * 1024 * 1024 + 1)
        message = "exceeds 5 MiB"
    else:
        for index in range(500):
            (skill / f"file-{index}").touch()
        message = "more than 500"
    with pytest.raises(AssessmentError, match=message):
        validate_package(skill)
