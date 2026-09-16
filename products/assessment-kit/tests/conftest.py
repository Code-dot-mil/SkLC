import json
import os

import pytest


@pytest.fixture(autouse=True)
def clean_assessor_environment(monkeypatch):
    for name in os.environ:
        if name.startswith(("SKLC_LLM_", "SKLC_SKILLSPECTOR_")) or name == "SKILLSPECTOR_BIN":
            monkeypatch.delenv(name)


@pytest.fixture
def make_skill():
    def create(parent, name="example-skill"):
        skill = parent / name
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(f"---\nname: {name}\ndescription: Test skill\n---\n\n# Test\n")
        return skill
    return create


@pytest.fixture
def skill(tmp_path, make_skill):
    return make_skill(tmp_path / "skills")


@pytest.fixture
def report():
    return {
        "execution_successful": True,
        "metadata": {"skillspector_version": "2.10.0", "llm_requested": False},
        "issues": [],
    }


@pytest.fixture
def scanner(tmp_path, monkeypatch, report):
    """A subprocess fixture that exercises the CLI's actual adapter boundary."""
    def install(exit_code=1):
        binary = tmp_path / "skillspector"
        binary.write_text(
            "#!/usr/bin/env python3\n"
            "import pathlib, sys\n"
            "if sys.argv[1:] == ['--version']:\n"
            "    print('skillspector 2.10.0')\n"
            "    raise SystemExit(0)\n"
            f"content = {json.dumps(report)!r}.encode()\n"
            "pathlib.Path(sys.argv[sys.argv.index('--output') + 1]).write_bytes(content)\n"
            f"raise SystemExit({exit_code})\n"
        )
        binary.chmod(0o755)
        monkeypatch.setenv("SKILLSPECTOR_BIN", str(binary))
        monkeypatch.setenv("SKLC_SKILLSPECTOR_SCAN_MODE", "static-only")
        return binary
    return install
