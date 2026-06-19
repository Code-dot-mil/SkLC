import json
from pathlib import Path

from skill_exchange.exchange_builder import build_exchange


def test_build_exchange_writes_index_boe_and_zip(tmp_path: Path):
    generated = tmp_path / "generated"

    result = build_exchange(
        skills_root=Path("tests/fixtures/skills"),
        exchange_dir=Path(".exchange"),
        generated_dir=generated,
        scanner="fixture",
        fixture="skillspector-clean.json",
    )

    assert result["skills_written"] == 1
    index = json.loads((generated / "index.json").read_text())
    assert index["skills"][0]["display_id"] == "ai4sdlc/sample-skill"
    assert index["skills"][0]["risk"] == "Low"
    assert "Low confidence" in index["skills"][0]["confidence_flags"]
    assert (generated / "zips" / "ai4sdlc--sample-skill.zip").exists()

    second = build_exchange(
        skills_root=Path("tests/fixtures/skills"),
        exchange_dir=Path(".exchange"),
        generated_dir=generated,
        scanner="fixture",
        fixture="skillspector-clean.json",
    )
    assert second["reused_scans"] == 1
