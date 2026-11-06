"""Select, assess, prune and summarize upstream CI reports through the public assessment CLI."""

import argparse
import html
import os
import subprocess
import sys
from pathlib import Path


def write_paths(path: Path, paths: list[Path]) -> None:
    path.write_bytes(b"".join(os.fsencode(item) + b"\0" for item in paths))


def read_paths(path: Path) -> list[Path]:
    return [Path(os.fsdecode(item)) for item in path.read_bytes().split(b"\0") if item]


def select(skills: Path, output: Path, base_sha: str | None) -> None:
    if not skills.is_dir():
        raise ValueError(f"Skill root does not exist: {skills}")
    skills = skills.resolve().relative_to(Path.cwd().resolve())
    changed_files = b""
    if base_sha is not None:
        base_sha = subprocess.check_output([
            "git", "rev-parse", "--verify", "--end-of-options", f"{base_sha}^{{commit}}",
        ], text=True).strip()
        changed_files = subprocess.check_output([
            "git", "diff", "--no-renames", "--name-only", "-z", f"{base_sha}...HEAD", "--", str(skills),
        ])
        changed = set()
        for item in changed_files.split(b"\0"):
            if item:
                relative = Path(os.fsdecode(item)).relative_to(skills)
                if len(relative.parts) > 1:
                    changed.add(skills / relative.parts[0])
    else:
        changed = {path.parent for path in skills.glob("*/SKILL.md") if path.is_file()}
    current = sorted(path for path in changed if (path / "SKILL.md").is_file())
    output.mkdir(parents=True, exist_ok=True)
    (output / "changed-files.nul").write_bytes(changed_files)
    write_paths(output / "changed-skills.nul", sorted(changed))
    write_paths(output / "current-skills.nul", current)
    print(f"Selected {len(current)} current packages; {len(changed) - len(current)} removed packages.")


def assess(selection: Path, reports: Path, before_sha: str | None, keep_going: bool) -> int:
    if before_sha is not None and before_sha != "0" * 40:
        # Validate even an empty selection before any later pruning or Git writes.
        subprocess.run(["git", "rev-parse", "--verify", "--end-of-options", f"{before_sha}^{{commit}}"],
                       check=True, stdout=subprocess.DEVNULL)
    result = 0
    for skill in read_paths(selection):
        output = reports / skill.name
        command = ["skill-assessment", "assess", "--skill", str(skill),
                   "--output-dir", str(output), "--scan-mode", "llm-assisted"]
        if before_sha is not None and before_sha != "0" * 40:
            comparison = subprocess.run([
                "git", "diff", "--quiet", before_sha, "HEAD", "--",
                str(output / "skillspector.json"), str(output / "adjudication.json"),
            ])
            if comparison.returncode == 0:
                command.append("--if-changed")
            elif comparison.returncode != 1:
                raise subprocess.CalledProcessError(comparison.returncode, comparison.args)
        status = subprocess.run(command).returncode
        if status:
            result = status
            if not keep_going:
                break
    return result


def prune(selection: Path, reports: Path) -> None:
    if reports.is_symlink():
        raise ValueError(f"Assessment root must not be a symlink: {reports}")
    current = {path.name for path in read_paths(selection)}
    for directory in reports.glob("*"):
        if directory.is_symlink() or not directory.is_dir() or directory.name in current:
            continue
        for name in ("skillspector.json", "adjudication.json", "scanner.log"):
            (directory / name).unlink(missing_ok=True)
        if not any(directory.iterdir()):
            directory.rmdir()


def summarize(reports: Path, output: Path, scan_outcome: str) -> int:
    output.mkdir(parents=True, exist_ok=True)
    result = 0
    with (output / "summary.md").open("w", encoding="utf-8") as combined:
        if scan_outcome != "success":
            combined.write("Assessment did not complete successfully; inspect retained diagnostics.\n\n")
        pairs = sorted(reports.rglob("adjudication.json"))
        if not pairs:
            combined.write("No retained report pairs could be summarized; inspect diagnostics.\n")
            return 1
        for adjudication in pairs:
            directory = adjudication.parent
            relative = directory.relative_to(reports)
            summary = output / "summaries" / relative / "summary.md"
            summary.parent.mkdir(parents=True, exist_ok=True)
            with summary.open("w", encoding="utf-8") as stream:
                status = subprocess.run(["skill-assessment", "summarize", "--assessment-dir", str(directory)],
                                        stdout=stream).returncode
            if status:
                result = 1
                combined.write("A retained report pair could not be summarized; inspect diagnostics.\n\n")
            else:
                combined.write(f"<h2>{html.escape(relative.parts[0])}</h2>\n\n")
                combined.write(summary.read_text(encoding="utf-8") + "\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    selection = commands.add_parser("select")
    selection.add_argument("--skills", type=Path, required=True)
    selection.add_argument("--output-dir", type=Path, required=True)
    selection.add_argument("--base-sha")
    assessment = commands.add_parser("assess")
    cleanup = commands.add_parser("prune")
    for command in (assessment, cleanup):
        command.add_argument("--selection", type=Path, required=True)
        command.add_argument("--reports", type=Path, required=True)
    assessment.add_argument("--before-sha")
    assessment.add_argument("--keep-going", action="store_true")
    summary = commands.add_parser("summarize")
    summary.add_argument("--reports", type=Path, required=True)
    summary.add_argument("--output-dir", type=Path, required=True)
    summary.add_argument("--scan-outcome", required=True)
    args = parser.parse_args()
    try:
        if args.command == "select":
            select(args.skills, args.output_dir, args.base_sha)
        elif args.command == "assess":
            return assess(args.selection, args.reports, args.before_sha, args.keep_going)
        elif args.command == "prune":
            prune(args.selection, args.reports)
        else:
            return summarize(args.reports, args.output_dir, args.scan_outcome)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Assessment CI failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
