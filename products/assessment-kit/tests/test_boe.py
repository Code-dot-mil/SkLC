from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from skill_assessment.artifacts import update_boe, verify_boe
from skill_assessment.errors import AssessmentError
from skill_assessment.packages import validate_package
from skill_assessment.skillspector import NativeReport


@pytest.fixture
def evidence(tmp_path):
    skill = tmp_path / "skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text("---\nname: skill\ndescription: Test\n---\n")
    package = validate_package(skill)
    native = b'{"metadata": {"skillspector_version": "unknown-future-version"}}\n'
    report = NativeReport(content=native, parsed=json.loads(native))
    root = tmp_path / "boe"
    manifest = update_boe(package, root, "skillspector", report)
    return package, root, manifest


def test_verified_boe_conforms_to_schema_without_full_assessor_validation(evidence):
    package, root, manifest = evidence
    schema_path = Path(__file__).parents[3] / "contracts/boe/v1/boe.schema.json"
    Draft202012Validator(json.loads(schema_path.read_text())).validate(json.loads(manifest.read_text()))
    verify_boe(package, root / package.name)


@pytest.mark.parametrize("damage", [
    "identity", "content", "missing-report", "wrong-digest", "wrong-filename",
    "escape", "absolute", "duplicate", "unknown-field", "unsupported-schema", "empty",
])
def test_verify_rejects_invalid_evidence(evidence, damage):
    package, root, manifest = evidence
    data = json.loads(manifest.read_text())
    entry = data["assessments"][0]
    report = manifest.parent / entry["path"]
    if damage == "identity":
        data["skill"]["name"] = "another-skill"
    elif damage == "content":
        (package.path / "SKILL.md").write_text("---\nname: skill\ndescription: Changed\n---\n")
        package = validate_package(package.path)
    elif damage == "missing-report":
        report.unlink()
    elif damage == "wrong-digest":
        entry["sha256"] = "sha256:" + "0" * 64
    elif damage == "wrong-filename":
        target = report.with_name("0" * 64 + ".json")
        report.rename(target)
        entry["path"] = target.relative_to(manifest.parent).as_posix()
    elif damage == "escape":
        entry["path"] = "../outside.json"
    elif damage == "absolute":
        entry["path"] = str(report)
    elif damage == "duplicate":
        data["assessments"].append(dict(entry))
    elif damage == "unknown-field":
        data["risk"] = "low"
    elif damage == "unsupported-schema":
        data["schema_version"] = "skill-exchange-boe/v0"
    elif damage == "empty":
        data["assessments"] = []
    manifest.write_text(json.dumps(data))
    with pytest.raises(AssessmentError):
        verify_boe(package, root / package.name)


@pytest.mark.parametrize("content", [
    b"not JSON", b"{}", b'{"metadata": {}}', b'{"metadata": {"skillspector_version": true}}',
])
def test_verify_requires_json_and_assessor_identity_even_with_matching_digest(evidence, content):
    package, root, manifest = evidence
    digest = hashlib.sha256(content).hexdigest()
    relative = f"assessments/skillspector/{digest}.json"
    (manifest.parent / relative).write_bytes(content)
    data = json.loads(manifest.read_text())
    data["assessments"] = [{"path": relative, "sha256": f"sha256:{digest}"}]
    manifest.write_text(json.dumps(data))
    with pytest.raises(AssessmentError):
        verify_boe(package, root / package.name)


def test_update_preserves_reports_and_rejects_changed_skill_without_new_files(evidence):
    package, root, manifest = evidence
    original = json.loads(manifest.read_text())["assessments"]
    native = b'{"metadata": {"assessor": "skillspector"}}'
    report = NativeReport(content=native, parsed=json.loads(native))
    update_boe(package, root, "skillspector", report)
    entries = json.loads(manifest.read_text())["assessments"]
    assert len(entries) == 2 and original[0] in entries
    assert entries == sorted(entries, key=lambda item: (item["path"], item["sha256"]))
    before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    (package.path / "SKILL.md").write_text("---\nname: skill\ndescription: Changed\n---\n")
    with pytest.raises(AssessmentError, match="does not match"):
        update_boe(validate_package(package.path), root, "skillspector", report)
    assert before == {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_verify_rejects_report_directory_symlink_escape(evidence, tmp_path):
    package, root, manifest = evidence
    directory = manifest.parent / "assessments/skillspector"
    outside = tmp_path / "outside"
    directory.rename(outside)
    directory.symlink_to(outside, target_is_directory=True)
    with pytest.raises(AssessmentError, match="safely read"):
        verify_boe(package, root / package.name)


@pytest.mark.parametrize("damage", ["missing", "corrupt"])
def test_update_refuses_damaged_existing_evidence_without_writing(evidence, damage):
    package, root, manifest = evidence
    existing = manifest.parent / json.loads(manifest.read_text())["assessments"][0]["path"]
    if damage == "missing":
        existing.unlink()
    else:
        existing.write_bytes(b"corrupt")
    before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    native = b'{"metadata": {"assessor": "skillspector"}}'
    with pytest.raises(AssessmentError):
        update_boe(package, root, "skillspector", NativeReport(native, json.loads(native)))
    assert before == {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
