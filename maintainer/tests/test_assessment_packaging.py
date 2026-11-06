"""Exercise the assessment download through its public packaging and reading commands."""

import shutil
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile

import pytest
from skill_assessment.errors import ScanError


@pytest.mark.parametrize("external_reports", [False, True])
def test_assessment_download_contains_readable_summary_from_selected_reports(tmp_path: Path, external_reports: bool):
    repository = Path(__file__).resolve().parents[2]
    source = tmp_path / "source"
    name = "code-change-description"
    skill = source / "products/skill-bundle" / name
    skill.parent.mkdir(parents=True)
    shutil.copytree(repository / "products/skill-bundle" / name, skill)
    committed = source / "products/skill-bundle-assessments"
    committed.mkdir()
    (committed / "README.md").write_text("Assessment download instructions\n")
    reports = tmp_path / "run-reports" if external_reports else committed
    shutil.copytree(repository / "products/skill-bundle-assessments" / name, reports / name)
    subprocess.run(["git", "init", "-q", str(source)], check=True)
    subprocess.run(["git", "-C", str(source), "add", "products"], check=True)
    subprocess.run([
        "git", "-C", str(source), "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
        "commit", "-qm", "Committed product input",
    ], check=True)
    inputs = {path: path.read_bytes() for path in reports.rglob("*") if path.is_file()}
    output = tmp_path / "skill-bundle-assessments.zip"
    command = [sys.executable, "-m", "sklc_maintainer.packaging", "assessments",
               "--repo-root", str(source), "--output", str(output)]
    if external_reports:
        command.extend(["--source-dir", str(reports)])
    subprocess.run(command, cwd=tmp_path, check=True, capture_output=True)

    extracted = tmp_path / "download"
    with ZipFile(output) as archive:
        assert set(archive.namelist()) == {
            "README.md", f"{name}/skillspector.json", f"{name}/adjudication.json", f"{name}/summary.md",
        }
        archive.extractall(extracted)
    for filename in ("skillspector.json", "adjudication.json"):
        assert (extracted / name / filename).read_bytes() == inputs[reports / name / filename]
    readable = subprocess.run([
        str(Path(sys.executable).with_name("skill-assessment")), "summarize",
        "--assessment-dir", str(extracted / name),
    ], cwd=tmp_path, check=True, capture_output=True, text=True).stdout
    assert (extracted / name / "summary.md").read_text() == readable
    assert {path: path.read_bytes() for path in reports.rglob("*") if path.is_file()} == inputs
    assert not list(source.rglob("summary.md"))


def test_invalid_report_pair_prevents_publishing_an_assessment_download(tmp_path: Path):
    from sklc_maintainer.packaging import package_assessments

    skill = tmp_path / "products/skill-bundle/example"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("Skill package\n")
    reports = tmp_path / "products/skill-bundle-assessments"
    (reports / "example").mkdir(parents=True)
    (reports / "README.md").write_text("Instructions\n")
    for filename in ("skillspector.json", "adjudication.json"):
        (reports / "example" / filename).write_text("{}\n")
    output = tmp_path / "assessments.zip"

    with pytest.raises(ScanError):
        package_assessments(tmp_path, output, None)
    assert not output.exists()
