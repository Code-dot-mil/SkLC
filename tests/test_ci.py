import json
import subprocess
from pathlib import Path

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
            "scanner_findings": [],
        }
    ]
    assert validation[0]["skill"] == "team/reviewed-skill"
    assert "| `team/reviewed-skill` | Low | Low confidence | static-only |" in comment
    assert "## Exchange validation" in comment


def test_review_comment_includes_all_scanner_findings(monkeypatch, tmp_path: Path):
    reviewed = _write_skill(tmp_path, "team", "reviewed-skill")
    artifacts = tmp_path / "review-artifacts"

    def fake_run_skillspector(skill_path, output_path, *, no_llm):
        assert skill_path == reviewed
        assert no_llm is False
        report = {
            "metadata": {"llm_requested": True, "skillspector_version": "2.1.5"},
            "risk_assessment": {"score": 35, "severity": "MEDIUM", "recommendation": "CAUTION"},
            "issues": [
                {
                    "id": "EA2",
                    "category": "Excessive Agency",
                    "pattern": "Autonomous Decision Making",
                    "severity": "MEDIUM",
                    "confidence": 0.75,
                    "location": {"file": "SKILL.md", "start_line": 12, "end_line": 14},
                    "finding": "without checking",
                    "explanation": "Skill enables autonomous high-impact decisions.",
                    "remediation": "Add human-in-the-loop confirmation.",
                    "code_snippet": "line one\nline two",
                },
                {
                    "id": "MP3",
                    "category": "Memory Poisoning",
                    "pattern": "Memory Manipulation",
                    "severity": "HIGH",
                    "confidence": 0.8,
                    "location": {"file": "SKILL.md", "start_line": 25},
                    "finding": "clear context",
                    "explanation": "Skill manipulates agent memory, state, or stored context.",
                    "remediation": "Protect agent memory and state from untrusted content.",
                    "code_snippet": "`[question]` - unclear context that could hide a real issue",
                },
            ],
        }
        output_path.parent.mkdir(parents=True)
        output_path.write_text(json.dumps(report))
        return report

    monkeypatch.setattr(ci, "run_skillspector", fake_run_skillspector)

    ci.review_changed_skills(
        changed_skill_paths=[reviewed],
        repo_root=tmp_path,
        exchange_dir=Path.cwd() / ".exchange",
        artifacts_dir=artifacts,
        scan_mode="llm-assisted",
        post_comment=False,
    )

    comment = (artifacts / "comment.md").read_text()

    assert "## Scanner findings" in comment
    assert "1. **MEDIUM** `EA2` - Excessive Agency / Autonomous Decision Making" in comment
    assert "2. **HIGH** `MP3` - Memory Poisoning / Memory Manipulation" in comment
    assert "Location: `SKILL.md:12-14`" in comment
    assert "Location: `SKILL.md:25`" in comment
    assert "Finding: without checking" in comment
    assert "Finding: clear context" in comment
    assert "Explanation: Skill enables autonomous high-impact decisions." in comment
    assert "Explanation: Skill manipulates agent memory, state, or stored context." in comment
    assert "Remediation: Add human-in-the-loop confirmation." in comment
    assert "Remediation: Protect agent memory and state from untrusted content." in comment
    assert "line one" in comment
    assert "`[question]` - unclear context that could hide a real issue" in comment


def test_parse_scan_modes_accepts_comma_and_space_separated_values():
    assert ci.parse_scan_modes("static-only,llm-assisted") == ("static-only", "llm-assisted")
    assert ci.parse_scan_modes("static-only llm-assisted") == ("static-only", "llm-assisted")


def test_commit_generated_outputs_force_adds_only_boe_bundle(monkeypatch, tmp_path: Path):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    (tmp_path / ".gitignore").write_text(
        ".exchange/generated/*\n!.exchange/generated/boe/\n!.exchange/generated/boe/**\n"
    )
    generated = tmp_path / ".exchange" / "generated"
    boe = generated / "boe" / "team" / "skill" / "hash" / "scan-key"
    tables = generated / "tables"
    zips = generated / "zips"
    boe.mkdir(parents=True)
    tables.mkdir(parents=True)
    zips.mkdir(parents=True)
    (boe / "boe.json").write_text('{"schema_version": "skill-exchange-boe/v0"}\n')
    (boe / "skillspector.json").write_text('{"issues": []}\n')
    (generated / "index.json").write_text('{"skills": []}\n')
    (tables / "scanner_runs.json").write_text('{"rows": []}\n')
    (zips / "team--skill.zip").write_bytes(b"zip")
    monkeypatch.setenv("EXCHANGE_PUBLISH_PUSH", "false")

    result = ci.commit_generated_outputs(repo_root=tmp_path, generated_dir=generated)

    assert result["committed"] is True
    assert result["path"] == ".exchange/generated/boe"
    tracked = subprocess.run(
        ["git", "ls-files", ".exchange/generated"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    assert tracked.stdout.splitlines() == [
        ".exchange/generated/boe/team/skill/hash/scan-key/boe.json",
        ".exchange/generated/boe/team/skill/hash/scan-key/skillspector.json",
    ]


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


def test_configure_push_remote_does_not_reuse_review_token_for_publish(monkeypatch, tmp_path: Path):
    calls = []

    def fake_run_git(repo_root: Path, *args: str):
        calls.append((repo_root, args))

    monkeypatch.setattr(ci, "run_git", fake_run_git)
    monkeypatch.delenv("EXCHANGE_PUBLISH_PUSH_URL", raising=False)
    monkeypatch.delenv("EXCHANGE_PUBLISH_TOKEN", raising=False)
    monkeypatch.delenv("EXCHANGE_PUBLISH_USERNAME", raising=False)
    monkeypatch.setenv("GITLAB_TOKEN", "review-comment-token")
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
