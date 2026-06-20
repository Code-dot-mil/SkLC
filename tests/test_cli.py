import json
import sys
from pathlib import Path

from skill_exchange import cli


def test_publish_local_accepts_generated_dir(monkeypatch, tmp_path: Path, capsys):
    calls = {}

    def fake_build_exchange(*, skills_root, exchange_dir, generated_dir, scan_modes):
        calls["skills_root"] = skills_root
        calls["exchange_dir"] = exchange_dir
        calls["generated_dir"] = generated_dir
        calls["scan_modes"] = scan_modes
        return {"skills_written": 0}

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
        ],
    )

    cli.main()

    assert calls == {
        "skills_root": Path("skills"),
        "exchange_dir": Path(".exchange"),
        "generated_dir": tmp_path / "local-generated",
        "scan_modes": ("static-only",),
    }
    assert json.loads(capsys.readouterr().out) == {"skills_written": 0}
