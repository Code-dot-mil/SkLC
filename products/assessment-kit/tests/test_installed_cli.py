"""Exercise an extracted release's installed wheel and the real pinned assessor.

Set SKLC_TEST_INSTALLED_CLI and SKLC_TEST_RELEASE_ROOT after installing the
archive's wheel and SkillSpector. Ordinary unit runs do not require a scanner.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator


def test_installed_cli_with_real_assessor(tmp_path):
    cli = os.environ.get("SKLC_TEST_INSTALLED_CLI")
    release_root = os.environ.get("SKLC_TEST_RELEASE_ROOT")
    if cli is None and release_root is None:
        pytest.skip("requires an installed release and real SkillSpector")
    if not cli or not cli.strip() or not release_root or not release_root.strip():
        pytest.fail("SKLC_TEST_INSTALLED_CLI and SKLC_TEST_RELEASE_ROOT must both be nonblank")
    cli = Path(cli).resolve(strict=True)
    contracts = Path(release_root) / "contracts"
    env = {k: v for k, v in os.environ.items() if not k.startswith(("SKLC_", "SKILLSPECTOR_", "PYTHON"))}
    env["SKILLSPECTOR_BIN"] = str(cli.parent / "skillspector")
    env["SKLC_SKILLSPECTOR_SCAN_MODE"] = "static-only"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    skills = tmp_path / "skills"
    for name in ("review", "tests"):
        skill = skills / name
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(f"---\nname: {name}\ndescription: Explain Python tests\n---\nRead the tests.\n")

    def invoke(*args):
        result = subprocess.run(
            [str(cli), *map(str, args)], cwd=tmp_path, env=env,
            capture_output=True, text=True, timeout=180,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        return result

    def validate_schema(value, relative):
        Draft202012Validator(json.loads((contracts / relative).read_text())).validate(value)

    invoke("--help")
    invoke("validate", "--root", skills)
    advice = tmp_path / "advice"
    invoke("advise", "--root", skills, "--assessor", "skillspector", "--output", advice)
    manifest = json.loads((advice / "advice-manifest.json").read_text())
    validate_schema(manifest, "assessment-artifacts/v1/advice-manifest.schema.json")
    assert manifest["skills"] == ["review", "tests"]
    assert len(manifest["native_reports"]) == 2
    assert manifest["advice_sha256"] == "sha256:" + hashlib.sha256((advice / "advice.md").read_bytes()).hexdigest()
    for entry in manifest["native_reports"]:
        raw = (advice / entry["path"]).read_bytes()
        assert entry["sha256"] == "sha256:" + hashlib.sha256(raw).hexdigest()
        native = json.loads(raw)
        assert native["execution_successful"] is True
        assert native["metadata"]["skillspector_version"] == "2.10.0"
    boe = tmp_path / "boe"
    invoke("assess", "--skill", skills / "review", "--skill", skills / "tests",
           "--assessor", "skillspector", "--boe-root", boe)
    for name in ("review", "tests"):
        manifest = json.loads((boe / name / "boe.json").read_text())
        validate_schema(manifest, "boe/v1/boe.schema.json")
        assert len(manifest["assessments"]) == 1
        invoke("verify-boe", "--skill", skills / name, boe / name)


@pytest.mark.parametrize("cli,release_root", [(None, "release"), ("cli", None), ("", "release"), ("cli", " ")])
def test_incomplete_installed_proof_configuration_fails(monkeypatch, tmp_path, cli, release_root):
    for name, value in (("SKLC_TEST_INSTALLED_CLI", cli), ("SKLC_TEST_RELEASE_ROOT", release_root)):
        if value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)
    with pytest.raises(pytest.fail.Exception, match="must both be nonblank"):
        test_installed_cli_with_real_assessor(tmp_path)
