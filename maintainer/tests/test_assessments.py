import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture
def repository(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PYTHONPATH", str(Path(__file__).resolve().parents[1] / "src"))

    def git(*args):
        return subprocess.check_output(["git", *args], text=True).strip()

    git("init", "-q")
    git("config", "user.name", "CI Test")
    git("config", "user.email", "ci@example.invalid")
    for name in ("a", "b"):
        skill = tmp_path / "bundle" / name
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(f"---\nname: {name}\ndescription: Test package\n---\nInstructions.\n")
        (skill / "reference.md").write_text("Supporting instructions")
        reports = tmp_path / "reports" / name
        reports.mkdir(parents=True)
        for filename in ("skillspector.json", "adjudication.json", "scanner.log"):
            (reports / filename).write_text("original")
    (tmp_path / "bundle/README.md").write_text("Bundle documentation")
    git("add", ".")
    git("commit", "-qm", "initial bundle")
    executable = tmp_path / "bin/skill-assessment"
    executable.parent.mkdir()
    # Exercise the real process boundary; assessment-kit owns report interpretation.
    executable.write_text(f"#!{sys.executable}\n" + '''import json, os, sys
from pathlib import Path
args = sys.argv[1:]
with open(os.environ["CALLS"], "a") as log:
    log.write(json.dumps(args) + "\\n")
if args[0] == "assess":
    directory = Path(args[args.index("--output-dir") + 1])
    directory.mkdir(parents=True, exist_ok=True)
    for name in ("skillspector.json", "adjudication.json", "scanner.log"):
        (directory / name).write_text("retained process output")
    if Path(args[args.index("--skill") + 1]).name == os.environ.get("FAIL_SKILL"):
        sys.exit(3)
else:
    if Path(args[-1]).name == os.environ.get("FAIL_SUMMARY"):
        sys.exit(1)
    print("Coverage is partial. Review retained evidence.")
''')
    executable.chmod(0o755)
    monkeypatch.setenv("PATH", f"{executable.parent}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("CALLS", str(tmp_path / "calls.jsonl"))

    def run(*args, success=True):
        result = subprocess.run([sys.executable, "-m", "sklc_maintainer.assessments", *args],
                                capture_output=True, text=True)
        assert (result.returncode == 0) == success, result.stderr
        return result

    def calls():
        path = tmp_path / "calls.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    return tmp_path, git, run, calls


def test_selection_tracks_supporting_changes_and_deletions_and_rejects_invalid_refs(repository):
    root, git, run, calls = repository
    base = git("rev-parse", "HEAD")
    (root / "bundle/a/reference.md").unlink()
    shutil.rmtree(root / "bundle/b")
    git("add", "-A")
    git("commit", "-qm", "change support and remove package")
    run("select", "--skills", "bundle", "--output-dir", "selection", "--base-sha", base)
    assert (root / "selection/changed-skills.nul").read_bytes() == b"bundle/a\0bundle/b\0"
    assert (root / "selection/current-skills.nul").read_bytes() == b"bundle/a\0"
    base = git("rev-parse", "HEAD")
    (root / "bundle/README.md").write_text("Unrelated documentation")
    git("add", "-A")
    git("commit", "-qm", "documentation only")
    run("select", "--skills", "bundle", "--output-dir", "selection", "--base-sha", base)
    assert not (root / "selection/current-skills.nul").read_bytes()
    for invalid in ("invalid", ""):
        run("select", "--skills", "bundle", "--output-dir", "invalid", "--base-sha", invalid, success=False)
    run("select", "--skills", "missing", "--output-dir", "invalid", success=False)
    assert not (root / "invalid").exists() and not calls()


@pytest.mark.parametrize("incoming", [None, "initial", "skillspector.json", "adjudication.json"])
def test_only_unchanged_incoming_pairs_allow_public_cli_reuse(repository, incoming):
    root, git, run, calls = repository
    before = git("rev-parse", "HEAD")
    if incoming == "initial":
        before = "0" * 40
    elif incoming:
        (root / "reports/a" / incoming).write_text("author changed report")
        git("add", "-A")
        git("commit", "-qm", "incoming report edit")
    run("select", "--skills", "bundle", "--output-dir", "selection")
    run("assess", "--selection", "selection/current-skills.nul", "--reports", "reports", "--before-sha", before)
    observed = {Path(call[call.index("--skill") + 1]).name: "--if-changed" in call for call in calls()}
    assert observed == {"a": incoming is None, "b": incoming != "initial"}


def test_pruning_retains_live_bytes_notes_and_symlinks_and_handles_last_skill_removal(repository):
    root, _, run, calls = repository
    for name in ("retired", "retired-with-notes"):
        directory = root / "reports" / name
        directory.mkdir()
        for filename in ("skillspector.json", "adjudication.json", "scanner.log"):
            (directory / filename).write_text("obsolete")
    (root / "reports/retired-with-notes/notes.md").write_text("keep")
    outside = root / "outside"
    outside.mkdir()
    (outside / "skillspector.json").write_text("untouched")
    (root / "reports/outside-link").symlink_to(outside, target_is_directory=True)
    live = {path: path.read_bytes() for path in (root / "reports/a").iterdir()}
    run("select", "--skills", "bundle", "--output-dir", "selection")
    run("prune", "--selection", "selection/current-skills.nul", "--reports", "reports")
    assert all(path.read_bytes() == data for path, data in live.items())
    assert not (root / "reports/retired").exists()
    assert sorted(path.name for path in (root / "reports/retired-with-notes").iterdir()) == ["notes.md"]
    assert (outside / "skillspector.json").read_text() == "untouched"
    for name in ("a", "b"):
        shutil.rmtree(root / "bundle" / name)
    run("select", "--skills", "bundle", "--output-dir", "selection")
    run("assess", "--selection", "selection/current-skills.nul", "--reports", "reports",
        "--before-sha", "invalid", success=False)
    assert all(path.read_bytes() == data for path, data in live.items()) and not calls()
    run("assess", "--selection", "selection/current-skills.nul", "--reports", "reports",
        "--before-sha", "0" * 40)
    run("prune", "--selection", "selection/current-skills.nul", "--reports", "reports")
    assert not (root / "reports/a").exists() and not (root / "reports/b").exists()


@pytest.mark.parametrize("keep_going", [False, True])
def test_partial_failures_retain_outputs_and_action_summaries(repository, monkeypatch, keep_going):
    root, _, run, calls = repository
    monkeypatch.setenv("FAIL_SKILL", "a")
    run("select", "--skills", "bundle", "--output-dir", "selection")
    result = run("assess", "--selection", "selection/current-skills.nul", "--reports", "reports",
                 *(["--keep-going"] if keep_going else []), success=False)
    assert result.returncode == 3 and len(calls()) == (2 if keep_going else 1)
    assert (root / "reports/a/scanner.log").read_text() == "retained process output"
    assert (root / "reports/b/scanner.log").read_text() == ("retained process output" if keep_going else "original")
    (root / "reports/b").rename(root / "reports/b<&")
    monkeypatch.setenv("FAIL_SUMMARY", "a")
    run("summarize", "--reports", "reports", "--output-dir", "review", "--scan-outcome", "failure", success=False)
    combined = (root / "review/summary.md").read_text()
    assert "did not complete" in combined and "could not be summarized" in combined
    assert "<h2>b&lt;&amp;</h2>" in combined and "Coverage is partial" in combined
    assert (root / "review/summaries/b<&/summary.md").read_text().startswith("Coverage is partial")
    run("summarize", "--reports", "missing-reports", "--output-dir", "empty-review",
        "--scan-outcome", "failure", success=False)
    assert "No retained report pairs" in (root / "empty-review/summary.md").read_text()


def test_workflow_commits_only_pairs_and_does_not_force_over_another_writer(repository):
    import yaml

    root, git, _, _ = repository
    workflow = Path(__file__).resolve().parents[2] / ".github/workflows/ci.yml"
    steps = yaml.safe_load(workflow.read_text())["jobs"]["bundle-assessments"]["steps"]
    body = next(step["run"] for step in steps if step.get("name") == "Commit current assessments")
    # An intentionally empty bundle has no matching tracked or untracked pairs.
    before = git("rev-parse", "HEAD")
    assert subprocess.run(["bash", "-e", "-c", body], capture_output=True).returncode == 0
    assert git("rev-parse", "HEAD") == before
    reports = root / "products/skill-bundle-assessments"
    shutil.copytree(root / "reports", reports)
    git("add", "products")
    git("commit", "-qm", "existing current pairs")
    remote = root.parent / f"{root.name}-remote.git"
    subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
    git("remote", "add", "origin", str(remote))
    git("push", "-q", "origin", "HEAD:main")
    (reports / "a/skillspector.json").write_text("new current pair")
    (reports / "b/adjudication.json").unlink()
    (reports / "b/skillspector.json").unlink()
    (reports / "a/scanner.log").write_text("new diagnostic")
    (reports / "notes.md").write_text("separately staged notes")
    git("add", "products/skill-bundle-assessments/notes.md")
    result = subprocess.run(["bash", "-e", "-c", body], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    committed = git("diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").splitlines()
    assert committed == [f"products/skill-bundle-assessments/{name}" for name in (
        "a/skillspector.json", "b/adjudication.json", "b/skillspector.json",
    )]
    assert git("diff", "--cached", "--name-only") == "products/skill-bundle-assessments/notes.md"
    for name in ("skillspector.json", "adjudication.json"):
        (reports / "a" / name).unlink()
    result = subprocess.run(["bash", "-e", "-c", body], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert not list(reports.glob("*/*.json"))
    tree = git("rev-parse", "HEAD^{tree}")
    other = subprocess.check_output(["git", "commit-tree", tree, "-p", "HEAD"],
                                    input="other writer\n", text=True).strip()
    subprocess.run(["git", "push", "-q", "origin", f"{other}:main"], check=True)
    for name in ("skillspector.json", "adjudication.json"):
        (reports / "a" / name).write_text("subsequent assessment")
    result = subprocess.run(["bash", "-e", "-c", body], capture_output=True, text=True)
    assert result.returncode != 0
    assert git("ls-remote", "origin", "refs/heads/main").split()[0] == other


def test_workflow_retains_summary_when_assessment_tooling_cannot_start(repository, monkeypatch):
    import yaml

    root, _, _, _ = repository
    workflow = Path(__file__).resolve().parents[2] / ".github/workflows/ci.yml"
    steps = yaml.safe_load(workflow.read_text())["jobs"]["pr-assessments"]["steps"]
    body = next(step["run"] for step in steps if step.get("name") == "Summarize findings and required actions")
    (root / "pr-assessments").mkdir()
    unavailable = root / "bin/uv"
    unavailable.write_text("#!/bin/sh\nexit 7\n")
    unavailable.chmod(0o755)
    monkeypatch.setenv("RUNNER_TEMP", str(root))
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(root / "actions-summary.md"))
    monkeypatch.setenv("SCAN_OUTCOME", "failure")
    result = subprocess.run(["bash", "-e", "-c", body], capture_output=True)
    assert result.returncode == 7
    retained = (root / "pr-assessments/summary.md").read_bytes()
    assert b"could not run" in retained and (root / "actions-summary.md").read_bytes() == retained


@pytest.mark.parametrize("skills,expected", [
    ([{"recommendation": "SAFE"}], 0),
    ([{"recommendation": "SAFE"}, {"recommendation": "CAUTION"}], 1),
    ([{"recommendation": "Unknown"}], 1),
    ([{}], 1),
    ([], 1),
])
def test_catalog_safety_gate_requires_safe_skills(tmp_path, monkeypatch, capsys, skills, expected):
    from sklc_maintainer.assessments import main

    for index, skill in enumerate(skills):
        skill["skill_id"] = f"skill-{index}"
    index = tmp_path / "index.json"
    index.write_text(json.dumps({"skills": skills}))
    monkeypatch.setattr(sys, "argv", ["assessments", "require-safe", "--index", str(index)])
    assert main() == expected
    if skills and expected:
        assert skills[-1]["skill_id"] in capsys.readouterr().err
