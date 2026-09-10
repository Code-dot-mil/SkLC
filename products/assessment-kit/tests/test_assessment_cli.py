from __future__ import annotations

import hashlib
import json
from pathlib import Path

from skill_assessment.cli import main


def make_skill(parent: Path, name: str = "example-skill") -> Path:
    skill = parent / name
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(f"---\nname: {name}\ndescription: Test skill\n---\n\n# Test\n")
    return skill


def make_skillspector(tmp_path: Path, report: dict, *, exit_code: int = 1) -> Path:
    binary = tmp_path / "skillspector"
    report_json = json.dumps(report)
    binary.write_text(
        "#!/usr/bin/env python3\n"
        "import pathlib, sys\n"
        "if sys.argv[1:] == ['--version']:\n"
        "    print('skillspector 2.10.0')\n"
        "    raise SystemExit(0)\n"
        f"content = {report_json!r}.encode()\n"
        "pathlib.Path(sys.argv[sys.argv.index('--output') + 1]).write_bytes(content)\n"
        f"raise SystemExit({exit_code})\n"
    )
    binary.chmod(0o755)
    return binary


def successful_report(*, issues: list[dict] | None = None) -> dict:
    return {
        "execution_successful": True,
        "metadata": {"skillspector_version": "2.10.0", "llm_requested": False},
        "issues": issues or [],
    }


def static_environment(monkeypatch, binary: Path) -> None:
    monkeypatch.setenv("SKILLSPECTOR_BIN", str(binary))
    monkeypatch.setenv("SKLC_SKILLSPECTOR_SCAN_MODE", "static-only")


def test_validate_command_writes_no_files(tmp_path: Path, capsys):
    skill = make_skill(tmp_path)

    assert main(["validate", "--skill", str(skill)]) == 0

    assert "valid example-skill sha256:" in capsys.readouterr().out
    assert list(tmp_path.iterdir()) == [skill]


def test_assess_retains_exact_report_and_verify_boe(monkeypatch, tmp_path: Path):
    skill = make_skill(tmp_path / "skills")
    report = successful_report()
    binary = make_skillspector(tmp_path, report)
    static_environment(monkeypatch, binary)
    boe_root = tmp_path / "boe"

    assert main(
        [
            "assess",
            "--skill",
            str(skill),
            "--assessor",
            "skillspector",
            "--boe-root",
            str(boe_root),
        ]
    ) == 0

    raw = json.dumps(report).encode()
    digest = hashlib.sha256(raw).hexdigest()
    report_path = boe_root / "example-skill" / "assessments" / "skillspector" / f"{digest}.json"
    assert report_path.read_bytes() == raw
    boe = json.loads((boe_root / "example-skill" / "boe.json").read_text())
    assert boe["assessments"] == [
        {"path": f"assessments/skillspector/{digest}.json", "sha256": f"sha256:{digest}"}
    ]
    assert main(["verify-boe", "--skill", str(skill), str(boe_root / "example-skill")]) == 0


def test_assess_is_idempotent(monkeypatch, tmp_path: Path):
    skill = make_skill(tmp_path / "skills")
    binary = make_skillspector(tmp_path, successful_report())
    static_environment(monkeypatch, binary)
    args = [
        "assess",
        "--skill",
        str(skill),
        "--assessor",
        "skillspector",
        "--boe-root",
        str(tmp_path / "boe"),
    ]

    assert main(args) == 0
    first = (tmp_path / "boe" / "example-skill" / "boe.json").read_bytes()
    assert main(args) == 0

    assert (tmp_path / "boe" / "example-skill" / "boe.json").read_bytes() == first
    assert len(json.loads(first)["assessments"]) == 1


def test_advise_preserves_actionable_finding_fields(monkeypatch, tmp_path: Path):
    skill = make_skill(tmp_path / "skills")
    report = successful_report(
        issues=[
            {
                "severity": "high",
                "category": "prompt-injection",
                "location": "SKILL.md:10",
                "finding": "Unsafe instruction",
                "pattern": "ignore prior",
                "confidence": "high",
                "explanation": "Overrides policy",
                "remediation": "Remove it",
            }
        ]
    )
    binary = make_skillspector(tmp_path, report, exit_code=0)
    static_environment(monkeypatch, binary)
    output = tmp_path / "advice"

    assert main(
        [
            "advise",
            "--skill",
            str(skill),
            "--assessor",
            "skillspector",
            "--output",
            str(output),
        ]
    ) == 0

    advice = (output / "advice.md").read_text()
    for value in ("high", "prompt-injection", "SKILL.md:10", "Unsafe instruction", "Remove it"):
        assert value in advice
    manifest = json.loads((output / "advice-manifest.json").read_text())
    assert manifest["skills"] == ["example-skill"]
    assert manifest["assessors"] == ["skillspector"]
    assert len(manifest["native_reports"]) == 1


def test_invalid_skill_fails_before_assessor_execution(monkeypatch, tmp_path: Path):
    skill = make_skill(tmp_path / "skills")
    (skill / "SKILL.md").write_text("not frontmatter")
    marker = tmp_path / "invoked"
    binary = tmp_path / "skillspector"
    binary.write_text(f"#!/bin/sh\ntouch {marker}\n")
    binary.chmod(0o755)
    static_environment(monkeypatch, binary)

    assert main(
        [
            "assess",
            "--skill",
            str(skill),
            "--assessor",
            "skillspector",
            "--boe-root",
            str(tmp_path / "boe"),
        ]
    ) == 2
    assert not marker.exists()
    assert not (tmp_path / "boe").exists()


def test_default_llm_mode_fails_closed_without_configuration(monkeypatch, tmp_path: Path, capsys):
    skill = make_skill(tmp_path / "skills")
    binary = make_skillspector(tmp_path, successful_report())
    monkeypatch.setenv("SKILLSPECTOR_BIN", str(binary))
    for name in (
        "SKLC_SKILLSPECTOR_SCAN_MODE",
        "SKLC_LLM_PROVIDER",
        "SKLC_LLM_API_KEY",
        "SKLC_LLM_BASE_URL",
        "SKLC_LLM_MODEL",
    ):
        monkeypatch.delenv(name, raising=False)

    assert main(
        [
            "assess",
            "--skill",
            str(skill),
            "--assessor",
            "skillspector",
            "--boe-root",
            str(tmp_path / "boe"),
        ]
    ) == 2

    assert "SKLC_LLM_API_KEY" in capsys.readouterr().err
    assert not (tmp_path / "boe").exists()


def test_degraded_llm_report_is_retryable_and_writes_nothing(monkeypatch, tmp_path: Path):
    skill = make_skill(tmp_path / "skills")
    report = {
        "execution_successful": True,
        "metadata": {
            "skillspector_version": "2.10.0",
            "llm_requested": True,
            "llm_available": False,
            "llm_degraded": True,
        },
    }
    binary = make_skillspector(tmp_path, report, exit_code=0)
    monkeypatch.setenv("SKILLSPECTOR_BIN", str(binary))
    monkeypatch.delenv("SKLC_SKILLSPECTOR_SCAN_MODE", raising=False)
    monkeypatch.setenv("SKLC_LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("SKLC_LLM_API_KEY", "do-not-print")
    monkeypatch.setenv("SKLC_LLM_BASE_URL", "https://example.invalid/v1")
    monkeypatch.setenv("SKLC_LLM_MODEL", "test-model")

    assert main(
        [
            "assess",
            "--skill",
            str(skill),
            "--assessor",
            "skillspector",
            "--boe-root",
            str(tmp_path / "boe"),
        ]
    ) == 10
    assert not (tmp_path / "boe").exists()


def test_verify_boe_detects_tampered_report(monkeypatch, tmp_path: Path):
    skill = make_skill(tmp_path / "skills")
    binary = make_skillspector(tmp_path, successful_report())
    static_environment(monkeypatch, binary)
    boe_root = tmp_path / "boe"
    args = [
        "assess",
        "--skill",
        str(skill),
        "--assessor",
        "skillspector",
        "--boe-root",
        str(boe_root),
    ]
    assert main(args) == 0
    report_path = next((boe_root / "example-skill" / "assessments").rglob("*.json"))
    report_path.write_text("{}")

    assert main(["verify-boe", "--skill", str(skill), str(boe_root / "example-skill")]) == 2


def test_empty_root_does_not_require_assessor_or_write_output(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("SKILLSPECTOR_BIN", raising=False)
    output = tmp_path / "advice"

    assert main(
        [
            "advise",
            "--root",
            str(tmp_path / "empty"),
            "--assessor",
            "skillspector",
            "--output",
            str(output),
        ]
    ) == 2

    (tmp_path / "empty").mkdir()
    assert main(
        [
            "advise",
            "--root",
            str(tmp_path / "empty"),
            "--assessor",
            "skillspector",
            "--output",
            str(output),
        ]
    ) == 0
    assert not output.exists()


def test_empty_root_still_rejects_invalid_configuration(tmp_path: Path):
    empty = tmp_path / "empty"
    empty.mkdir()
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"assessors": {"unknown": {}}}))

    assert main(
        [
            "advise",
            "--root",
            str(empty),
            "--assessor",
            "skillspector",
            "--output",
            str(tmp_path / "output"),
            "--config",
            str(config),
        ]
    ) == 2


def test_output_inside_skill_is_rejected(monkeypatch, tmp_path: Path):
    skill = make_skill(tmp_path)
    binary = make_skillspector(tmp_path, successful_report())
    static_environment(monkeypatch, binary)

    assert main(
        [
            "advise",
            "--skill",
            str(skill),
            "--assessor",
            "skillspector",
            "--output",
            str(skill / "generated"),
        ]
    ) == 2
    assert not (skill / "generated").exists()
