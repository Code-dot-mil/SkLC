import argparse

from .commands import assess, hash, summarize, validate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="skill-assessment", description="Skill assessment commands.")
    commands = parser.add_subparsers(dest="command", required=True)
    validate.register(commands)
    assess.register(commands)
    hash.register(commands)
    summarize.register(commands)
    args = parser.parse_args(argv)
    return args.handler(args)
