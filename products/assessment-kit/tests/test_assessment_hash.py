import json
from pathlib import Path

import pytest
from skill_assessment.cli import main

# Captured from assess's package-v1 algorithm before exposing the hash command.
PACKAGE_DIGEST = "4ee6de3544cb14641f0f181d9b2a67ac172308976937b87ed4dec7166d60795e"


def test_hash_matches_existing_algorithm_and_assessment(skill, scanner, tmp_path, capsys):
    (skill / "references").mkdir()
    (skill / "references" / "usage.md").write_bytes(b"Additional guidance.\n")
    assert main(["hash", "--skill", str(skill)]) == 0
    captured = capsys.readouterr()
    assert captured.out == PACKAGE_DIGEST + "\n"
    assert captured.err == ""

    output = tmp_path / "boe"
    assert main(["assess", "--skill", str(skill), "--output-dir", str(output)]) == 0
    adjudication = json.loads((output / "adjudication.json").read_text())
    assert adjudication["skill_sha256"] == PACKAGE_DIGEST


def test_hash_tracks_supporting_file_contents_and_paths(skill, capsys):
    support = skill / "usage.md"
    support.write_bytes(b"Original guidance.\n")
    assert main(["hash", "--skill", str(skill)]) == 0
    original = capsys.readouterr().out

    support.write_bytes(b"Updated guidance.\n")
    assert main(["hash", "--skill", str(skill)]) == 0
    assert capsys.readouterr().out != original

    support.write_bytes(b"Original guidance.\n")
    support.rename(skill / "renamed.md")
    assert main(["hash", "--skill", str(skill)]) == 0
    assert capsys.readouterr().out != original


def test_hash_is_stable_across_location_order_and_empty_directories(skill, tmp_path, capsys, monkeypatch):
    (skill / "z.md").write_bytes(b"Last\n")
    (skill / "a.md").write_bytes(b"First\n")
    assert main(["hash", "--skill", str(skill)]) == 0
    original = capsys.readouterr().out

    copy = tmp_path / "copy"
    copy.mkdir()
    for name in ("a.md", "z.md", "SKILL.md"):
        (copy / name).write_bytes((skill / name).read_bytes())
    (copy / "empty").mkdir()
    monkeypatch.chdir(copy)
    assert main(["hash", "--skill", "."]) == 0
    assert capsys.readouterr().out == original


@pytest.mark.parametrize("kind", ["missing", "file", "unreadable"])
def test_hash_reports_invalid_input_without_stdout(skill, capsys, monkeypatch, kind):
    target = skill
    if kind == "missing":
        target = skill / "missing"
    elif kind == "file":
        target = skill / "SKILL.md"
    else:
        def unreadable(path):
            raise PermissionError("read denied")
        monkeypatch.setattr(Path, "read_bytes", unreadable)

    assert main(["hash", "--skill", str(target)]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err


@pytest.mark.parametrize("args", [[], ["--skill", "one", "--skill", "two"]])
def test_hash_requires_one_explicit_directory(args):
    with pytest.raises(SystemExit) as error:
        main(["hash", *args])
    assert error.value.code == 2
