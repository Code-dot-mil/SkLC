import json
import subprocess
from pathlib import Path

import yaml
from skill_exchange import ci


def _write_skill(root: Path, namespace: str, skill_id: str, description: str = "Use when testing CI.") -> Path:
    skill_dir = root / "skills" / namespace / skill_id
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        f"""---
name: {skill_id}
description: {description}
metadata:
  ai4sdlc.category: testing
  ai4sdlc.tags: unit-tests
  ai4sdlc.owner: test-owner
---

# {skill_id}
"""
    )
    return skill_dir


def test_changed_skill_paths_detects_skill_roots_only(tmp_path: Path):
    _write_skill(tmp_path, "team", "reviewed-skill")
    _write_skill(tmp_path, "team", "other-skill")

    changed = ci.changed_skill_paths_from_names(
        [
            "site/src/pages/index.astro",
            "skills/team/reviewed-skill/SKILL.md",
            "skills/team/reviewed-skill/references/note.md",
            "skills/team/missing-skill/README.md",
        ],
        repo_root=tmp_path,
        skills_root=Path("skills"),
    )

    assert changed == [
        tmp_path / "skills" / "team" / "missing-skill",
        tmp_path / "skills" / "team" / "reviewed-skill",
    ]


def test_review_changed_skills_writes_reviewer_artifacts(monkeypatch, tmp_path: Path):
    reviewed = _write_skill(tmp_path, "team", "reviewed-skill")
    _write_skill(tmp_path, "team", "other-skill")
    artifacts = tmp_path / "review-artifacts"

    def fake_run_skillspector(skill_path, output_path, *, no_llm):
        assert skill_path == reviewed
        assert no_llm is True
        report = {
            "metadata": {"llm_requested": False, "skillspector_version": "2.1.5"},
            "risk_assessment": {"score": 0, "severity": "LOW", "recommendation": "SAFE"},
            "issues": [],
        }
        output_path.parent.mkdir(parents=True)
        output_path.write_text(json.dumps(report))
        return report

    monkeypatch.setattr(ci, "run_skillspector", fake_run_skillspector)

    result = ci.review_changed_skills(
        changed_skill_paths=[reviewed],
        repo_root=tmp_path,
        exchange_dir=Path.cwd() / ".exchange",
        artifacts_dir=artifacts,
        scan_mode="static-only",
        post_comment=False,
    )

    changed_skills = json.loads((artifacts / "changed-skills.json").read_text())
    validation = json.loads((artifacts / "validation.json").read_text())
    comment = (artifacts / "comment.md").read_text()

    assert result["reviewed_skills"] == 1
    assert result["validation_errors"] == 0
    assert changed_skills == [
        {
            "skill": "team/reviewed-skill",
            "risk": "Low",
            "reason": "No medium, high, or critical findings detected.",
            "confidence_flags": ["Low confidence"],
            "scan_mode": "static-only",
            "report": str(artifacts / "skillspector" / "team" / "reviewed-skill" / "report.json"),
            "scanner_error": None,
        }
    ]
    assert validation[0]["skill"] == "team/reviewed-skill"
    assert "| `team/reviewed-skill` | Low | Low confidence | static-only |" in comment


def test_parse_scan_modes_accepts_comma_and_space_separated_values():
    assert ci.parse_scan_modes("static-only,llm-assisted") == ("static-only", "llm-assisted")
    assert ci.parse_scan_modes("static-only llm-assisted") == ("static-only", "llm-assisted")


def test_commit_generated_outputs_force_adds_ignored_generated_files(monkeypatch, tmp_path: Path):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    (tmp_path / ".gitignore").write_text(".exchange/generated/**\n!.exchange/generated/.gitkeep\n")
    generated = tmp_path / ".exchange" / "generated"
    generated.mkdir(parents=True)
    (generated / "index.json").write_text('{"skills": []}\n')
    monkeypatch.setenv("EXCHANGE_PUBLISH_PUSH", "false")

    result = ci.commit_generated_outputs(repo_root=tmp_path, generated_dir=generated)

    assert result["committed"] is True
    tracked = subprocess.run(
        ["git", "ls-files", ".exchange/generated/index.json"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    assert tracked.stdout.strip() == ".exchange/generated/index.json"


def test_configure_push_remote_uses_ci_job_token_when_no_publish_token(monkeypatch, tmp_path: Path):
    calls = []

    def fake_run_git(repo_root: Path, *args: str):
        calls.append((repo_root, args))

    monkeypatch.setattr(ci, "run_git", fake_run_git)
    monkeypatch.delenv("EXCHANGE_PUBLISH_PUSH_URL", raising=False)
    monkeypatch.delenv("EXCHANGE_PUBLISH_TOKEN", raising=False)
    monkeypatch.delenv("GITLAB_TOKEN", raising=False)
    monkeypatch.delenv("EXCHANGE_PUBLISH_USERNAME", raising=False)
    monkeypatch.setenv("CI_JOB_TOKEN", "job-token-value")
    monkeypatch.setenv("CI_SERVER_PROTOCOL", "https")
    monkeypatch.setenv("CI_SERVER_HOST", "gitlab.example.invalid")
    monkeypatch.setenv("CI_PROJECT_PATH", "group/project")

    ci.configure_push_remote(tmp_path)

    assert calls == [
        (
            tmp_path,
            (
                "remote",
                "set-url",
                "origin",
                "https://gitlab-ci-token:job-token-value@gitlab.example.invalid/group/project.git",
            ),
        )
    ]


def test_gitlab_ci_routes_jobs_by_expected_changes():
    config = yaml.safe_load(Path(".gitlab-ci.yml").read_text())

    assert config["variables"]["PYTHON_IMAGE_REGISTRY"] == "docker.io"
    assert config["variables"]["PYTHON_IMAGE_REPOSITORY"] == "library/python"
    assert config["variables"]["PYTHON_IMAGE_TAG"] == "3.12-bookworm"
    assert config["variables"]["PYTHON_BOOTSTRAP_COMMAND"] == "python -m pip install --no-cache-dir uv"
    assert config["variables"]["NODE_IMAGE_REGISTRY"] == "docker.io"
    assert config["variables"]["PYTHON_IMAGE"] == "$PYTHON_IMAGE_REGISTRY/$PYTHON_IMAGE_REPOSITORY:$PYTHON_IMAGE_TAG"
    assert config["variables"]["NODE_IMAGE"] == "$NODE_IMAGE_REGISTRY/$NODE_IMAGE_REPOSITORY:$NODE_IMAGE_TAG"
    assert config["variables"]["SKILL_EXCHANGE_RUNNER_TAG"] == "mitre-no-cui"
    assert config["variables"]["PAGES_RUNNER_TAG"] == "pages-no-cui"
    assert config["variables"]["EXCHANGE_PUBLISH_USERNAME"] == ""
    assert config[".python_job"]["tags"] == ["$SKILL_EXCHANGE_RUNNER_TAG"]
    assert config[".node_job"]["tags"] == ["$SKILL_EXCHANGE_RUNNER_TAG"]
    for job_name in [".python_job", "review:skills", "publish:exchange"]:
        assert config[job_name]["before_script"][0] == (
            'if [ -n "$PYTHON_BOOTSTRAP_COMMAND" ]; then sh -c "$PYTHON_BOOTSTRAP_COMMAND"; fi'
        )
    assert config["review:skills"]["rules"] == [
        {"if": '$CI_PIPELINE_SOURCE == "merge_request_event"', "changes": ["skills/**/*"]}
    ]
    assert config["pages"]["tags"] == ["$PAGES_RUNNER_TAG"]
    assert config["pages"]["rules"] == [
        {"if": '$CI_PIPELINE_SOURCE == "schedule"'},
        {"if": '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH && $CI_PIPELINE_SOURCE == "push"'}
    ]
    for job_name in ["lint:python", "lint:site", "test:python", "test:site", "audit:python", "audit:site"]:
        rule_changes = config[job_name]["rules"][0]["changes"]
        assert "skills/**/*" not in rule_changes
        assert "site/**/*" in rule_changes
        assert "scripts/**/*" in rule_changes
    assert "uv run ruff check scripts tests" in config["lint:python"]["script"]
