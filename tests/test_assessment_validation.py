from pathlib import Path

import pytest
from skill_assessment.cli import main


@pytest.fixture
def skill(tmp_path: Path) -> Path:
    path = tmp_path / "my-skill"
    path.mkdir()
    (path / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: Help with a task.\ncustom: allowed\n---\n# Instructions\n",
        encoding="utf-8",
    )
    return path


def test_validates_relative_directory_without_exchange_context(skill, monkeypatch, capsys):
    before = (skill / "SKILL.md").read_bytes()
    monkeypatch.chdir(skill)
    assert main(["validate", "--skill", "."]) == 0
    assert capsys.readouterr().out == "Valid skill: .\n"
    assert list(skill.iterdir()) == [skill / "SKILL.md"]
    assert (skill / "SKILL.md").read_bytes() == before


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("# No metadata", "must start with YAML frontmatter"),
        ("---\nname: my-skill", "closing marker not found"),
        ("---\nname: [broken\n---", "Invalid skill"),
        ("---\n- item\n---", "must be a mapping"),
        ("---\n---", "must be a mapping"),
        ("---\ndescription: Task\n---", "name must be a nonempty string"),
        ("---\nname: 42\ndescription: Task\n---", "name must be a nonempty string"),
        ("---\nname: ' '\ndescription: Task\n---", "name must be a nonempty string"),
        ("---\nname: my-skill\n---", "description must be a nonempty string"),
        ("---\nname: my-skill\ndescription: ' '\n---", "description must be a nonempty string"),
        ("---\nname: my-skill\ndescription: [Task]\n---", "description must be a nonempty string"),
        ("---\nname: another-skill\ndescription: Task\n---", "name must match the skill directory"),
    ],
)
def test_rejects_invalid_metadata(skill, text, message, capsys):
    (skill / "SKILL.md").write_text(text, encoding="utf-8")
    assert main(["validate", "--skill", str(skill)]) == 1
    captured = capsys.readouterr()
    assert message in captured.err
    assert captured.out == ""


@pytest.mark.parametrize("input_kind", ["missing-directory", "file", "missing-skill-md", "bad-encoding"])
def test_rejects_unreadable_inputs(skill, input_kind, capsys):
    selected = skill
    if input_kind == "missing-directory":
        selected = skill / "absent"
    elif input_kind == "file":
        selected = skill / "SKILL.md"
    elif input_kind == "missing-skill-md":
        (skill / "SKILL.md").unlink()
    else:
        (skill / "SKILL.md").write_bytes(b"\xff")
    assert main(["validate", "--skill", str(selected)]) == 1
    assert "Invalid skill" in capsys.readouterr().err


def test_reports_read_permission_error(skill, monkeypatch, capsys):
    def unreadable(*args, **kwargs):
        raise PermissionError("read denied")

    monkeypatch.setattr(Path, "read_text", unreadable)
    assert main(["validate", "--skill", str(skill)]) == 1
    assert "read denied" in capsys.readouterr().err


@pytest.mark.parametrize("args", [
    [], ["validate"], ["advise"], ["validate", "--skill", "one", "two"],
    ["validate", "--skill", "one", "--skill", "two"],
])
def test_requires_one_explicit_skill(args):
    with pytest.raises(SystemExit) as error:
        main(args)
    assert error.value.code == 2
