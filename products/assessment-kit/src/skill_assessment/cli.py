from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .artifacts import update_boe, verify_boe, write_advice
from .config import load_skillspector_config, validate_assessors
from .errors import AssessmentError
from .packages import reject_output_overlap, select_packages, validate_package
from .skillspector import require_supported_version, resolve_binary, run


def _selection(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--skill", action="append", type=Path, dest="skills")
    group.add_argument("--root", type=Path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="skill-assessment")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    validate = commands.add_parser("validate", help="validate unpacked skill packages")
    _selection(validate)

    for name, output_flag in (("advise", "--output"), ("assess", "--boe-root")):
        command = commands.add_parser(name, help=f"{name} unpacked skill packages")
        _selection(command)
        command.add_argument("--assessor", action="append", required=True)
        command.add_argument(output_flag, type=Path, required=True)
        command.add_argument("--config", type=Path)

    verify = commands.add_parser("verify-boe", help="verify BOE for one skill package")
    verify.add_argument("--skill", type=Path, required=True)
    verify.add_argument("boe_directory", type=Path)
    return parser


def dispatch(args: argparse.Namespace) -> int:
    if args.command == "verify-boe":
        package = validate_package(args.skill)
        verify_boe(package, args.boe_directory)
        print(f"verified BOE for {package.name}")
        return 0

    packages = select_packages(skill_paths=args.skills, root=args.root)
    if args.command == "validate":
        for package in packages:
            print(f"valid {package.name} sha256:{package.content_sha256}")
        return 0
    assessors = validate_assessors(args.assessor)
    config = load_skillspector_config(args.config, require_llm_values=bool(packages))
    output_argument = args.output if args.command == "advise" else args.boe_root
    try:
        output = output_argument.expanduser().resolve()
    except (OSError, RuntimeError) as exc:
        raise AssessmentError(f"cannot resolve command output directory: {output_argument}") from exc
    reject_output_overlap(output, packages)
    if not packages:
        return 0
    binary = resolve_binary()
    require_supported_version(binary)
    reports = []
    exit_code = 0
    for package in packages:
        for assessor_id in assessors:
            try:
                report = run(package.path, config, binary=binary, output_root=output)
                if report.diagnostics:
                    print(f"{package.name}/{assessor_id}: {report.diagnostics}", file=sys.stderr)
                if args.command == "assess":
                    update_boe(package, output, assessor_id, report)
                else:
                    reports.append((package, assessor_id, report))
            except AssessmentError as exc:
                exit_code = max(exit_code, exc.exit_code)
                print(f"{package.name}/{assessor_id}: {exc}", file=sys.stderr)
    if reports:
        try:
            write_advice(output, packages, assessors, reports)
        except AssessmentError as exc:
            exit_code = max(exit_code, exc.exit_code)
            print(f"advice: {exc}", file=sys.stderr)
    return exit_code


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    try:
        return dispatch(parser.parse_args(argv))
    except AssessmentError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code
    except (OSError, UnicodeError) as exc:
        print(f"error: cannot complete assessment: {exc}", file=sys.stderr)
        return AssessmentError.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
