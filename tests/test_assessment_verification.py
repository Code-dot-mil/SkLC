import json
from pathlib import Path

import pytest
from skill_assessment.cli import main


def make_boe(root: Path) -> Path:
    root.mkdir()
    index = root / "index.json"
    index.write_text(json.dumps({
        "boe_schema_version": 1,
        "assessments": [{"path": "scan-a"}, {"path": "scan-b"}],
    }))
    for scan in ("scan-a", "scan-b"):
        directory = root / scan
        directory.mkdir()
        for name in ("skillspector.json", "adjudication.json"):
            (directory / name).write_bytes(b"opaque output, not JSON\xff")
    return index


def snapshot(root: Path) -> dict[str, bytes | None]:
    return {str(path.relative_to(root)): path.read_bytes() if path.is_file() else None
            for path in root.rglob("*")}


def test_verifies_every_listed_scan_without_reading_or_changing_outputs(tmp_path, monkeypatch):
    index = make_boe(tmp_path / "boe")
    before = snapshot(tmp_path)
    monkeypatch.chdir(tmp_path.parent)

    assert main(["verify-boe", "--index", str(index)]) == 0
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("name", ["skillspector.json", "adjudication.json"])
@pytest.mark.parametrize("directory_instead", [False, True])
def test_missing_output_in_later_scan_fails_without_repair(tmp_path, capsys, name, directory_instead):
    index = make_boe(tmp_path / "boe")
    missing = index.parent / "scan-b" / name
    missing.unlink()
    if directory_instead:
        missing.mkdir()
    before = snapshot(tmp_path)

    assert main(["verify-boe", "--index", str(index)]) == 4
    assert name in capsys.readouterr().err
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("version", [0, 2, "1", 1.0, True, None])
def test_incompatible_schema_version_fails_without_changes(tmp_path, version):
    index = make_boe(tmp_path / "boe")
    document = json.loads(index.read_text())
    document["boe_schema_version"] = version
    index.write_text(json.dumps(document))
    before = snapshot(tmp_path)

    assert main(["verify-boe", "--index", str(index)]) == 4
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("contents", ["{", "[]", "{}", '{"boe_schema_version": 1, "assessments": [null]}'])
def test_malformed_index_fails_without_changes(tmp_path, capsys, contents):
    index = tmp_path / "index.json"
    index.write_text(contents)
    before = snapshot(tmp_path)

    assert main(["verify-boe", "--index", str(index)]) == 4
    assert "index" in capsys.readouterr().err.lower()
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("directory_instead", [False, True])
def test_unreadable_index_fails_without_changes(tmp_path, capsys, directory_instead):
    index = tmp_path / "index.json"
    if directory_instead:
        index.mkdir()
    before = snapshot(tmp_path)

    assert main(["verify-boe", "--index", str(index)]) == 4
    assert "index" in capsys.readouterr().err.lower()
    assert snapshot(tmp_path) == before
