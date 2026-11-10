import json
import subprocess
import sys

import pytest


@pytest.mark.parametrize("recommendation", ["SAFE", "CAUTION", "Unknown", None])
def test_catalog_gate_requires_every_skill_to_be_safe(tmp_path, recommendation):
    skill = {"skill_id": "review", "adjudication": {
        "summary": "Review rationale", "coverage_sufficient": False,
    }}
    if recommendation is not None:
        skill["recommendation"] = recommendation
    index = tmp_path / "index.json"
    index.write_text(json.dumps({"skills": [
        {"skill_id": "documentation", "recommendation": "SAFE"}, skill,
    ]}))
    result = subprocess.run(
        [sys.executable, "-m", "sklc_maintainer.safety_gate", "--index", str(index)],
        capture_output=True, text=True,
    )
    assert result.returncode == (0 if recommendation == "SAFE" else 1)
    if recommendation != "SAFE":
        assert "review" in result.stderr and "Review rationale" in result.stderr


def test_empty_catalog_cannot_pass_safety_gate(tmp_path):
    index = tmp_path / "index.json"
    index.write_text('{"skills": []}')
    result = subprocess.run(
        [sys.executable, "-m", "sklc_maintainer.safety_gate", "--index", str(index)],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
