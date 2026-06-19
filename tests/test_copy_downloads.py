import json
import subprocess
from pathlib import Path


SCRIPT = Path("site/scripts/copy-downloads.mjs").resolve()


def _run_copy_downloads(site_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["node", str(SCRIPT)],
        cwd=site_dir,
        text=True,
        capture_output=True,
        check=False,
    )


def test_copy_downloads_rejects_source_outside_generated_tree(tmp_path: Path):
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    generated_tables = tmp_path / ".exchange" / "generated" / "tables"
    generated_tables.mkdir(parents=True)
    (tmp_path / "secret.txt").write_text("secret\n")
    (generated_tables / "scanner_artifacts.json").write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "path": "secret.txt",
                        "download_path": "/downloads/scanner-runs/run-1/secret.txt",
                    }
                ]
            }
        )
    )

    completed = _run_copy_downloads(site_dir)

    assert completed.returncode != 0
    assert "outside .exchange/generated/scanner-runs" in completed.stderr
    assert not (site_dir / "public" / "downloads" / "scanner-runs" / "run-1" / "secret.txt").exists()


def test_copy_downloads_rejects_destination_outside_downloads(tmp_path: Path):
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    scanner_run = tmp_path / ".exchange" / "generated" / "scanner-runs" / "run-1"
    scanner_run.mkdir(parents=True)
    (scanner_run / "skillspector.json").write_text("{}\n")
    tables = tmp_path / ".exchange" / "generated" / "tables"
    tables.mkdir(parents=True, exist_ok=True)
    (tables / "scanner_artifacts.json").write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "path": ".exchange/generated/scanner-runs/run-1/skillspector.json",
                        "download_path": "/../src/pages/overwrite.astro",
                    }
                ]
            }
        )
    )

    completed = _run_copy_downloads(site_dir)

    assert completed.returncode != 0
    assert "outside public/downloads" in completed.stderr
    assert not (site_dir / "src" / "pages" / "overwrite.astro").exists()

