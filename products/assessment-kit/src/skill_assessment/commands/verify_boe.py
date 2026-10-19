import argparse
import json
import sys
from pathlib import Path

from ..errors import EvidenceError


def verify_boe(index_path: Path) -> None:
    """Check the BOE format version and presence of each listed scan's outputs."""
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise EvidenceError(f"Cannot read BOE index {index_path}: {exc}") from exc
    try:
        version = index["boe_schema_version"]
        if type(version) is not int or version != 1:
            raise EvidenceError(f"Unsupported BOE schema version: {version!r}; expected 1")
        for entry in index["assessments"]:
            directory = index_path.parent / entry["path"]
            for name in ("skillspector.json", "adjudication.json"):
                output = directory / name
                if not output.is_file():
                    raise EvidenceError(f"Missing BOE output: {output}")
    except (KeyError, TypeError, ValueError, OSError) as exc:
        raise EvidenceError(f"Malformed BOE index {index_path}: {exc}") from exc


def register(subparsers) -> None:
    parser = subparsers.add_parser("verify-boe", help="Check the BOE version and listed scan output files.")
    parser.add_argument("--index", type=Path, required=True, help="Path to the BOE index.json.")
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    try:
        verify_boe(args.index)
    except EvidenceError as exc:
        print(str(exc), file=sys.stderr)
        return 4
    print(f"Verified BOE: {args.index}")
    return 0
