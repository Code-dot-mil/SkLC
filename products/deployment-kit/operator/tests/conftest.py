import json
import shutil
from pathlib import Path

import pytest
from skill_assessment.hashing import skill_digest


@pytest.fixture
def current_assessment(tmp_path):
    skills = tmp_path / "skills"
    shutil.copytree(Path(__file__).parent / "fixtures/skills", skills)
    skill = skills / "sample-skill"
    directory = tmp_path / "assessments/sample-skill"
    directory.mkdir(parents=True)
    report = {
        "execution_successful": True,
        "analysis_completeness": {"is_complete": False, "opaque_provider_field": "retained"},
        "metadata": {"llm_requested": True, "llm_available": True},
        "risk_assessment": {"score": 80, "severity": "HIGH", "recommendation": "DO_NOT_INSTALL"},
        "issues": [
            {
                "id": rule,
                "category": "Execution",
                "pattern": "Code execution",
                "severity": "HIGH",
                "location": {"file": "run.py", "start_line": index},
                "finding": "eval(input)",
                "explanation": "Untrusted input reaches eval",
                "remediation": "Parse data without eval",
                "code_snippet": "eval(input)",
            }
            for index, rule in enumerate(["CE1", "CE1", "NET1"], 1)
        ],
    }
    adjudication = {
        "status": "completed",
        "safe_to_use": False,
        "summary": "Review execution and destination.",
        "coverage_sufficient": False,
        "coverage_reason": "One destination remains unresolved.",
        "scope": "SKILL.md and scanner evidence only.",
        "skill_sha256": skill_digest(skill),
        "metadata": {"created_at": "2026-10-19T12:00:00+00:00"},
        "findings": [
            {"index": index, "rule_id": issue["id"], "determination": determination, "reason": reason}
            for index, (issue, determination, reason) in enumerate(
                zip(
                    report["issues"],
                    ["true_positive", "false_positive", "uncertain"],
                    ["Executes input", "Inert example", "Unknown destination"],
                    strict=True,
                ),
                1,
            )
        ],
    }

    def save():
        (directory / "skillspector.json").write_text(json.dumps(report))
        (directory / "adjudication.json").write_text(json.dumps(adjudication))
        (directory / "scanner.log").write_text("retained scanner diagnostics\n")

    save()
    return skills, directory, report, adjudication, save
