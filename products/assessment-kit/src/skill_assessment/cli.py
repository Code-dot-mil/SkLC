import argparse
import sys
from pathlib import Path

import yaml


def validate_skill(skill: Path) -> None:
    skill = skill.resolve()
    if not skill.is_dir():
        raise ValueError("select a skill directory")
    lines = (skill / "SKILL.md").read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        raise ValueError("SKILL.md must start with YAML frontmatter")
    try:
        end = lines.index("---", 1)
    except ValueError:
        raise ValueError("SKILL.md frontmatter closing marker not found") from None
    metadata = yaml.safe_load("\n".join(lines[1:end]))
    if not isinstance(metadata, dict):
        raise ValueError("SKILL.md frontmatter must be a mapping")
    for key in ("name", "description"):
        value = metadata.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{key} must be a nonempty string")
    if metadata["name"] != skill.name:
        raise ValueError(f"name must match the skill directory: expected {skill.name!r}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="skill-assessment", description="Validate a skill package.")
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="Check one skill directory and its SKILL.md metadata.")
    validate.add_argument("--skill", type=Path, action="append", required=True, help="Path to one skill directory.")
    args = parser.parse_args(argv)
    if len(args.skill) != 1:
        parser.error("select exactly one --skill directory")
    skill = args.skill[0]
    try:
        validate_skill(skill)
    except (OSError, UnicodeError, ValueError, yaml.YAMLError) as exc:
        print(f"Invalid skill {skill}: {exc}", file=sys.stderr)
        return 1
    print(f"Valid skill: {skill}")
    return 0
