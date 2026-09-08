from __future__ import annotations

import argparse
import json
from pathlib import Path

from .exchange_builder import build_exchange

SCAN_MODES = ("static-only", "llm-assisted")
CATALOG_SKILLS_ROOT = Path("products/skill-catalog/skills")
EXCHANGE_ROOT = Path("maintainer/exchange")


def main() -> None:
    parser = argparse.ArgumentParser()
    subcommands = parser.add_subparsers(dest="command", required=True)

    publish = subcommands.add_parser("publish-local")
    publish.add_argument("--generated-dir", type=Path, default=EXCHANGE_ROOT / "generated")
    publish.add_argument("--scan-mode", choices=SCAN_MODES, action="append")
    publish.add_argument("--reuse-boe-only", action="store_true")

    args = parser.parse_args()
    if args.command == "publish-local":
        result = build_exchange(
            skills_root=CATALOG_SKILLS_ROOT,
            exchange_dir=EXCHANGE_ROOT,
            generated_dir=args.generated_dir,
            scan_modes=tuple(args.scan_mode or SCAN_MODES),
            reuse_boe_only=args.reuse_boe_only,
        )
        if args.reuse_boe_only and result["skills_written"] == 0:
            raise RuntimeError("tracked BOE generation produced an empty catalog")
        print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
