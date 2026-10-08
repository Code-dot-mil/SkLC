from __future__ import annotations

import argparse
import json
from pathlib import Path

from .exchange_builder import build_exchange

SCAN_MODES = ("static-only", "llm-assisted")


def main() -> None:
    parser = argparse.ArgumentParser()
    subcommands = parser.add_subparsers(dest="command", required=True)

    publish = subcommands.add_parser("publish-local")
    publish.add_argument("--generated-dir", type=Path, default=Path(".exchange/generated"))
    publish.add_argument("--scan-mode", choices=SCAN_MODES, action="append")
    publish.add_argument("--boe-dir", type=Path, default=Path(".exchange/generated/boe"))

    args = parser.parse_args()
    if args.command == "publish-local":
        result = build_exchange(
            skills_root=Path("skills"),
            exchange_dir=Path(".exchange"),
            generated_dir=args.generated_dir,
            scan_modes=tuple(args.scan_mode or ("static-only",)),
            boe_dir=args.boe_dir,
        )
        if result["skills_written"] == 0:
            raise RuntimeError("tracked BOE generation produced an empty catalog")
        print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
