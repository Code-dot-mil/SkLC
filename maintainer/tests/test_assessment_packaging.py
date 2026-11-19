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


@pytest.fixture
def product_checkout(tmp_path):
    """Use authentic tracked product inputs, isolated from upstream working files."""
    import io
    import tarfile

    repository = Path(__file__).resolve().parents[2]
    source = tmp_path / "source"
    source.mkdir()
    snapshot = subprocess.check_output(["git", "-C", str(repository), "archive", "HEAD", "products"])
    with tarfile.open(fileobj=io.BytesIO(snapshot)) as archive:
        archive.extractall(source, filter="data")
    def git(*args):
        return subprocess.check_output(["git", "-C", str(source), *args], text=True).strip()
    git("init", "-q")
    git("add", ".")
    git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "Product inputs")
    git("tag", "v1.2.3")
    def package(*args, success=True):
        result = subprocess.run([
            sys.executable, "-m", "sklc_maintainer.packaging", args[0], "--repo-root", str(source), *args[1:],
        ], cwd=tmp_path, capture_output=True, text=True)
        assert (result.returncode == 0) == success, result.stderr
        return result
    return source, package


def test_product_downloads_compose_committed_inputs(product_checkout, tmp_path):
    source, package = product_checkout
    name = "code-change-description"
    skill_file = source / f"products/skill-bundle/{name}/SKILL.md"
    committed_skill = skill_file.read_bytes()
    skill_file.write_text("Uncommitted replacement must not ship")
    bundle = tmp_path / "bundle.zip"
    evidence = tmp_path / "evidence.zip"
    package("bundle", "--output", str(bundle))
    package("assessments", "--output", str(evidence))
    # Packaging treats the wheel as an opaque supplied artifact; installation is a separate workflow.
    wheel = tmp_path / "skill_assessment-1.2.3-py3-none-any.whl"
    wheel.write_bytes(b"supplied wheel fixture")
    package("operator", "--bundle", str(bundle), "--assessments", str(evidence),
            "--wheel", str(wheel), "--version", "1.2.3", "--output-dir", str(tmp_path))
    with ZipFile(bundle) as archive:
        assert archive.read(f"skills/{name}/SKILL.md") == committed_skill
    with ZipFile(tmp_path / "deployment-kit-operator-1.2.3.zip") as archive:
        assert archive.read(f"upstream/skills/{name}/SKILL.md") == committed_skill
        assert archive.read(f"assessment/{wheel.name}") == wheel.read_bytes()
        assert archive.read("assessment/requirements.txt").decode().strip() == f"./assessment/{wheel.name}"
        for path in (".gitlab-ci.yml", "ci/assessment.yml", "src/skill_exchange/cli.py", "site/package.json"):
            assert archive.read(path)
        with ZipFile(evidence) as reports:
            for report in ("skillspector.json", "adjudication.json"):
                assert archive.read(f"upstream/evidence/{name}/{report}") == reports.read(f"{name}/{report}")
    site = tmp_path / "built-site"
    site.mkdir()
    (site / "index.html").write_text("Finished site")
    (site / ".gitkeep").touch()
    for mode in (("--stage",), ("--version", "1.2.3")):
        package("prebuilt", *mode, "--site-dir", str(site), "--output-dir", str(tmp_path / "prebuilt"))
    with ZipFile(tmp_path / "prebuilt/deployment-kit-prebuilt-1.2.3.zip") as archive:
        assert archive.read("public/index.html") == b"Finished site"
        assert "public/.gitkeep" not in archive.namelist()
        for path in (".gitlab-ci.yml", "README.md", "docs/install.md", "docs/deploy-gitlab-pages.md"):
            assert archive.read(path)


@pytest.mark.parametrize("problem", ["stale-evidence", "unsafe-path"])
def test_operator_rejects_invalid_bundle_without_publishing(product_checkout, tmp_path, problem):
    _, package = product_checkout
    bundle = tmp_path / "bundle.zip"
    evidence = tmp_path / "evidence.zip"
    package("bundle", "--output", str(bundle))
    package("assessments", "--output", str(evidence))
    with ZipFile(bundle, "a") as archive:
        path = "../escaped.txt" if problem == "unsafe-path" else "skills/code-change-description/added.md"
        archive.writestr(path, "Unassessed content")
    wheel = tmp_path / "assessment.whl"
    wheel.write_bytes(b"opaque supplied wheel")
    package("operator", "--bundle", str(bundle), "--assessments", str(evidence), "--wheel", str(wheel),
            "--version", "1.2.3", "--output-dir", str(tmp_path), success=False)
    assert not (tmp_path / "deployment-kit-operator-1.2.3.zip").exists()
    assert not (tmp_path / "escaped.txt").exists()
