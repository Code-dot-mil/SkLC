import json
import os
import shutil
from zipfile import ZipFile

import pytest
from skill_assessment.hashing import skill_digest
from skill_exchange.builder import build_exchange


def generate(current_assessment, output):
    skills, directory, *_ = current_assessment
    return build_exchange(skills_root=skills, generated_dir=output, assessments_dir=directory.parent)


def set_dates(current_assessment, metadata):
    skills, _, _, adjudication, save = current_assessment
    skill = skills / "sample-skill"
    source = skill / "SKILL.md"
    source.write_text(source.read_text().replace("metadata:\n", metadata or "metadata:\n", 1))
    adjudication["skill_sha256"] = skill_digest(skill)
    save()


def test_skill_dates_survive_copying_and_timestamp_changes(current_assessment, tmp_path):
    set_dates(current_assessment, 'metadata:\n  ai4sdlc.created: "2026-06-19T19:49:27-05:00"\n'
              '  ai4sdlc.updated: "2026-10-20T14:59:35-05:00"\n')
    output = tmp_path / "generated"
    generate(current_assessment, output)
    original = (output / "index.json").read_bytes()
    record = json.loads(original)["skills"][0]
    assert record["first_observed"] == "2026-06-20T00:49:27+00:00"
    assert record["last_updated"] == "2026-10-20T19:59:35+00:00"
    skills, *_ = current_assessment
    copied = tmp_path / "extracted-skills"
    shutil.copytree(skills, copied)
    for path in copied.rglob("*"):
        if path.is_file():
            os.utime(path, (1700000000, 1700000000))
    generate((copied, *current_assessment[1:]), output)
    assert (output / "index.json").read_bytes() == original


@pytest.mark.parametrize("metadata,created,updated", [
    ("", None, None),
    ('metadata:\n  ai4sdlc.created: "2026-06-19T00:00:00Z"\n', "2026-06-19T00:00:00+00:00", None),
    ('metadata:\n  ai4sdlc.updated: "2026-10-20T00:00:00Z"\n', None, "2026-10-20T00:00:00+00:00"),
])
def test_unknown_dates_are_not_invented(current_assessment, tmp_path, metadata, created, updated):
    set_dates(current_assessment, metadata)
    output = tmp_path / "generated"
    generate(current_assessment, output)
    record = json.loads((output / "index.json").read_text())["skills"][0]
    assert record["first_observed"] == created
    assert record["last_updated"] == updated


@pytest.mark.parametrize("metadata", [
    'metadata:\n  ai4sdlc.created: "not-a-date"\n',
    'metadata:\n  ai4sdlc.updated: "2026-02-30T00:00:00Z"\n',
    'metadata:\n  ai4sdlc.created: "2026-06-19T00:00:00"\n',
    'metadata:\n  ai4sdlc.updated: 42\n',
    'metadata:\n  ai4sdlc.created: "2026-10-20T00:00:00Z"\n  ai4sdlc.updated: "2026-06-19T00:00:00Z"\n',
])
def test_invalid_dates_preserve_published_output(current_assessment, tmp_path, metadata):
    output = tmp_path / "generated"
    generate(current_assessment, output)
    before = {path: path.read_bytes() for path in output.rglob("*") if path.is_file()}
    set_dates(current_assessment, metadata)
    with pytest.raises(ValueError):
        generate(current_assessment, output)
    assert {path: path.read_bytes() for path in output.rglob("*") if path.is_file()} == before


def test_current_pair_becomes_adjudication_and_exact_downloads(current_assessment, tmp_path):
    skills, directory, _, adjudication, _ = current_assessment
    before = {path: path.read_bytes() for path in directory.iterdir()}
    output = tmp_path / "generated"
    assert generate(current_assessment, output) == {"skills_written": 1}
    record = json.loads((output / "index.json").read_text())["skills"][0]
    assert record["skill_id"] == "sample-skill"
    assert record["last_scanned"] is None
    assert record["adjudication"]["summary"] == adjudication["summary"]
    assert not list(output.rglob("scanner.log")), "scanner logs remain diagnostics, not site downloads"
    for key, download in record["assessment_downloads"].items():
        assert (output / download.removeprefix("downloads/")).read_bytes() == before[directory / f"{key}.json"]
    with ZipFile(output / "zips/sample-skill.zip") as archive:
        assert archive.read("sample-skill/SKILL.md") == (skills / "sample-skill/SKILL.md").read_bytes()
    generate(current_assessment, output)
    assert {path: path.read_bytes() for path in directory.iterdir()} == before


def test_false_positives_and_partial_coverage_remain_publishable(current_assessment, tmp_path):
    _, _, _, adjudication, save = current_assessment
    for finding in adjudication["findings"]:
        finding["determination"] = "false_positive"
    adjudication.update(safe_to_use=True, coverage_sufficient=True)
    save()
    generate(current_assessment, tmp_path / "generated")
    record = json.loads((tmp_path / "generated/index.json").read_text())["skills"][0]
    assert record["adjudication"]["summary"] == adjudication["summary"]


def test_supporting_file_change_rejects_stale_assessment(current_assessment, tmp_path):
    skills, directory, *_ = current_assessment
    before = {path: path.read_bytes() for path in directory.iterdir()}
    (skills / "sample-skill/reference.md").write_text("changed supporting guidance")
    with pytest.raises(ValueError, match="current skill content"):
        generate(current_assessment, tmp_path / "generated")
    assert {path: path.read_bytes() for path in directory.iterdir()} == before


@pytest.mark.parametrize("invalid", ["index", "rule_id", "missing", "incomplete", "execution", "static"])
def test_invalid_pair_cannot_replace_published_output(current_assessment, tmp_path, invalid):
    _, _, report, adjudication, save = current_assessment
    output = tmp_path / "generated"
    generate(current_assessment, output)
    before = {path: path.read_bytes() for path in output.rglob("*") if path.is_file()}
    if invalid == "execution":
        report["execution_successful"] = False
    elif invalid == "static":
        report["metadata"]["llm_requested"] = False
        adjudication["status"] = "not_performed"
    elif invalid == "incomplete":
        adjudication["status"] = "failed"
    elif invalid == "missing":
        adjudication["findings"].pop()
    else:
        adjudication["findings"][0][invalid] = 2 if invalid == "index" else "OTHER"
    save()
    with pytest.raises(ValueError):
        generate(current_assessment, output)
    assert {path: path.read_bytes() for path in output.rglob("*") if path.is_file()} == before


@pytest.mark.parametrize("filename", ["skillspector.json", "adjudication.json"])
def test_current_assessment_rejects_symlinked_reports(current_assessment, tmp_path, filename):
    _, directory, *_ = current_assessment
    path = directory / filename
    outside = tmp_path / filename
    path.rename(outside)
    path.symlink_to(outside)
    with pytest.raises(ValueError, match="regular files"):
        generate(current_assessment, tmp_path / "generated")


def test_rebuild_removes_obsolete_generated_downloads(current_assessment, tmp_path):
    output = tmp_path / "generated"
    for name in ("zips", "skills", "scanner-runs", "tables", "assessments"):
        directory = output / name
        directory.mkdir(parents=True)
        (directory / "removed").write_text("stale output")
    generate(current_assessment, output)
    assert not list(output.rglob("removed"))


@pytest.mark.parametrize("input_name", ["skills", "evidence"])
@pytest.mark.parametrize("overlap", ["output-inside", "equal", "input-inside"])
def test_overlapping_roots_preserve_inputs(current_assessment, tmp_path, input_name, overlap):
    skills, directory, *_ = current_assessment
    evidence = directory.parent
    input_root = skills if input_name == "skills" else evidence
    if overlap == "input-inside":
        output = input_root.parent
    else:
        output = input_root if overlap == "equal" else input_root / "generated"
    before = {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    with pytest.raises(ValueError, match="must not overlap"):
        build_exchange(skills_root=skills, assessments_dir=evidence, generated_dir=output)
    assert {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()} == before


def test_generated_symlink_is_rejected_before_old_output_is_removed(current_assessment, tmp_path):
    output = tmp_path / "generated"
    (output / "zips").mkdir(parents=True)
    (output / "zips/retained.zip").write_bytes(b"previous build")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "retained.json").write_bytes(b"unrelated")
    (output / "assessments").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        generate(current_assessment, output)
    assert (output / "zips/retained.zip").read_bytes() == b"previous build"
    assert (outside / "retained.json").read_bytes() == b"unrelated"
