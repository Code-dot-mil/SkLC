import sys
from pathlib import Path

from ..hashing import skill_digest


def register(subparsers) -> None:
    parser = subparsers.add_parser("hash", help="Print one skill package's SHA-256.")
    parser.add_argument("--skill", type=Path, action="append", required=True)
    parser.set_defaults(handler=run, command_parser=parser)


def run(args) -> int:
    if len(args.skill) != 1:
        args.command_parser.error("select exactly one --skill directory")
    try:
        skill = args.skill[0].resolve()
        if not skill.is_dir():
            raise ValueError("select a skill directory")
        digest = skill_digest(skill)
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(digest)
    return 0
