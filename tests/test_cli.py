import json
import sys
from pathlib import Path

from skill_exchange import cli


def test_publish_local_accepts_generated_dir_and_reuse_boe_only(monkeypatch, tmp_path: Path, capsys):
    calls = {}

    def fake_build_exchange(*, skills_root, exchange_dir, generated_dir, scan_modes, reuse_boe_only):
        calls["skills_root"] = skills_root
        calls["exchange_dir"] = exchange_dir
        calls["generated_dir"] = generated_dir
        calls["scan_modes"] = scan_modes
        calls["reuse_boe_only"] = reuse_boe_only
        return {"skills_written": 1}

    monkeypatch.setattr(cli, "build_exchange", fake_build_exchange)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "skill-exchange",
            "publish-local",
            "--generated-dir",
            str(tmp_path / "local-generated"),
            "--scan-mode",
            "static-only",
            "--reuse-boe-only",
        ],
    )

    cli.main()

    assert calls == {
        "skills_root": Path("skills"),
        "exchange_dir": Path(".exchange"),
        "generated_dir": tmp_path / "local-generated",
        "scan_modes": ("static-only",),
        "reuse_boe_only": True,
    }
    assert json.loads(capsys.readouterr().out) == {"skills_written": 1}
