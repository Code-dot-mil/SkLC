from pathlib import Path

import pytest
from skill_assessment.cli import main
from skill_assessment.commands.validate import COMMAND_ARG_NAME as VALIDATE_COMMAND
from skill_assessment.commands.validate import SKILL_OPTION_FLAG as SKILL_OPTION
from skill_assessment.commands.validate import validate_skill
from skill_assessment.errors import (
    InvalidSkillDirectoryError,
    InvalidSkillFrontmatterKeyError,
    MalformedFrontmatterError,
    MissingFrontmatterError,
    NonMappingFrontmatterError,
    SkillNameMismatchError,
    UnclosedFrontmatterError,
)


@pytest.fixture
def mock_skill_dir(tmp_path: Path) -> Path:
    path = tmp_path / "my-skill"
    path.mkdir()
    (path / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: Help with a task.\ncustom: allowed\n---\n# Instructions\n",
        encoding="utf-8",
    )
    return path


def test_validates_relative_directory_without_exchange_context(mock_skill_dir, monkeypatch):
    # Arrange
    before = (mock_skill_dir / "SKILL.md").read_bytes()
    monkeypatch.chdir(mock_skill_dir)

    # Act
    exit_code = main([VALIDATE_COMMAND, SKILL_OPTION, "."])

    # Assert
    assert exit_code == 0
    assert list(mock_skill_dir.iterdir()) == [mock_skill_dir / "SKILL.md"]
    assert (mock_skill_dir / "SKILL.md").read_bytes() == before


@pytest.mark.parametrize(
    ("frontmatter_text", "error_type"),
    [
        ("# No metadata", MissingFrontmatterError),
        ("---\nname: my-skill", UnclosedFrontmatterError),
        ("---\nname: [broken\n---", MalformedFrontmatterError),
        ("---\n- item\n---", NonMappingFrontmatterError),
        ("---\n---", NonMappingFrontmatterError),
        ("---\ndescription: Task\n---", InvalidSkillFrontmatterKeyError),
        ("---\nname: 42\ndescription: Task\n---", InvalidSkillFrontmatterKeyError),
        ("---\nname: ' '\ndescription: Task\n---", InvalidSkillFrontmatterKeyError),
        ("---\nname: my-skill\n---", InvalidSkillFrontmatterKeyError),
        ("---\nname: my-skill\ndescription: ' '\n---", InvalidSkillFrontmatterKeyError),
        ("---\nname: my-skill\ndescription: [Task]\n---", InvalidSkillFrontmatterKeyError),
        ("---\nname: another-skill\ndescription: Task\n---", SkillNameMismatchError),
    ],
)
def test_rejects_invalid_metadata(mock_skill_dir, frontmatter_text, error_type):
    # Arrange
    (mock_skill_dir / "SKILL.md").write_text(frontmatter_text, encoding="utf-8")

    # Act
    with pytest.raises(error_type):
        validate_skill(mock_skill_dir)
    exit_code = main([VALIDATE_COMMAND, SKILL_OPTION, str(mock_skill_dir)])

    # Assert
    assert exit_code == 1


@pytest.mark.parametrize(("input_kind", "error_type"), [
    ("missing-directory", InvalidSkillDirectoryError),
    ("file", InvalidSkillDirectoryError),
    ("missing-skill-md", FileNotFoundError),
    ("bad-encoding", UnicodeDecodeError),
])
def test_rejects_unreadable_inputs(mock_skill_dir, input_kind, error_type):
    # Arrange
    skill_dir_input = mock_skill_dir
    if input_kind == "missing-directory":
        skill_dir_input = mock_skill_dir / "not-a-dir"
    elif input_kind == "file":
        skill_dir_input = mock_skill_dir / "SKILL.md"
    elif input_kind == "missing-skill-md":
        (mock_skill_dir / "SKILL.md").unlink()
    elif input_kind == "bad-encoding":
        (mock_skill_dir / "SKILL.md").write_bytes(b"\xff")

    # Act
    with pytest.raises(error_type):
        validate_skill(skill_dir_input)
    exit_code = main([VALIDATE_COMMAND, SKILL_OPTION, str(skill_dir_input)])

    # Assert
    assert exit_code == 1


def test_reports_read_permission_error(mock_skill_dir, monkeypatch):
    # Arrange
    def unreadable(*args, **kwargs):
        raise PermissionError("read denied")

    monkeypatch.setattr(Path, "read_text", unreadable)

    # Act
    with pytest.raises(PermissionError):
        validate_skill(mock_skill_dir)
    exit_code = main([VALIDATE_COMMAND, SKILL_OPTION, str(mock_skill_dir)])

    # Assert
    assert exit_code == 1


@pytest.mark.parametrize("args", [
    [], [VALIDATE_COMMAND], ["advise"], [VALIDATE_COMMAND, SKILL_OPTION, "one", "two"],
    [VALIDATE_COMMAND, SKILL_OPTION, "one", SKILL_OPTION, "two"],
])
def test_requires_one_explicit_skill(args):
    # Arrange: invalid invocations are supplied by the parameterized cases.

    # Act
    with pytest.raises(SystemExit) as error:
        main(args)

    # Assert
    assert error.value.code == 2
