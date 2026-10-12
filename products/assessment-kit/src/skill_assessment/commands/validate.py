import argparse
import sys
from pathlib import Path

import yaml

from ..errors import (
    InvalidSkillDirectoryError,
    InvalidSkillFrontmatterKeyError,
    MalformedFrontmatterError,
    MissingFrontmatterError,
    NonMappingFrontmatterError,
    SkillNameMismatchError,
    SkillValidationError,
    UnclosedFrontmatterError,
)

COMMAND_ARG_NAME = "validate"
SKILL_OPTION_FLAG = "--skill"


def validate_skill(skill: Path) -> None:
    skill = skill.resolve()
    if not skill.is_dir():
        raise InvalidSkillDirectoryError("select a skill directory")
    lines = (skill / "SKILL.md").read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        raise MissingFrontmatterError("SKILL.md must start with YAML frontmatter")
    try:
        end = lines.index("---", 1)
    except ValueError:
        raise UnclosedFrontmatterError("SKILL.md frontmatter closing marker not found") from None
    try:
        metadata = yaml.safe_load("\n".join(lines[1:end]))
    except yaml.YAMLError as exc:
        raise MalformedFrontmatterError(str(exc)) from exc
    if not isinstance(metadata, dict):
        raise NonMappingFrontmatterError("SKILL.md frontmatter must be a mapping")
    # name and description are the required SKILL.md frontmatter keys.
    for key in ("name", "description"):
        value = metadata.get(key)
        if not isinstance(value, str) or not value.strip():
            raise InvalidSkillFrontmatterKeyError(f"{key} must be a nonempty string")
    if metadata["name"] != skill.name:
        raise SkillNameMismatchError(f"name must match the skill directory: expected {skill.name!r}")


def register(subparsers) -> None:
    parser = subparsers.add_parser(COMMAND_ARG_NAME, help="Check one skill directory and its SKILL.md metadata.")
    parser.add_argument(
        SKILL_OPTION_FLAG, type=Path, action="append", required=True, help="Path to one skill directory."
    )
    parser.set_defaults(handler=run, command_parser=parser)


def run(args: argparse.Namespace) -> int:
    if len(args.skill) != 1:
        args.command_parser.error(f"select exactly one {SKILL_OPTION_FLAG} directory")
    skill = args.skill[0]
    try:
        validate_skill(skill)
    except (OSError, UnicodeError, SkillValidationError) as exc:
        print(f"Invalid skill {skill}: {exc}", file=sys.stderr)
        return 1
    print(f"Valid skill: {skill}")
    return 0
