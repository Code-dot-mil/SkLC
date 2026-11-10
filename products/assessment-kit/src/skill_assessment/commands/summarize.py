"""Explain remediation, unresolved findings, and false positives from paired reports."""

import json
import re
import sys
from pathlib import Path

from ..adjudication import validate_finding, validate_verdict
from ..errors import ScanError
from ..reports import load_scanner_report, validate_assessment_report


def markdown(value: object) -> str:
    """Keep untrusted report text on one line and escape Markdown/HTML syntax."""
    text = " ".join(str(value).split())
    return re.sub(r"([\\`*_{}\[\]()#+.!|<>~&-])", r"\\\1", text)


def summarize(directory: Path) -> str:
    report = load_scanner_report(directory / "skillspector.json")
    verdict = json.loads((directory / "adjudication.json").read_text(encoding="utf-8"))
    issues, findings = report["issues"], verdict["findings"]
    if not isinstance(findings, list) or len(issues) != len(findings):
        raise ValueError("Every scanner finding requires a paired determination")
    status = verdict["status"]
    if status == "completed":
        validate_verdict({key: verdict[key] for key in (
            "safe_to_use", "summary", "coverage_sufficient", "coverage_reason", "findings"
        )}, issues, enforce_coverage=verdict.get("metadata", {}).get("enforce_coverage", True))
    elif status not in {"not_performed", "unavailable", "failed"}:
        raise ValueError("Unknown adjudication status")
    if status != "completed":
        for index, (issue, finding) in enumerate(zip(issues, findings, strict=True), 1):
            # Non-completed artifacts use not_adjudicated; reuse the public identity/reason checks.
            checked = dict(finding)
            if status != "completed" and checked.get("determination") == "not_adjudicated":
                checked["determination"] = "uncertain"
            validate_finding(checked, issue, index)

    groups = {name: [] for name in ("true_positive", "unresolved", "false_positive")}
    for index, (issue, finding) in enumerate(zip(issues, findings, strict=True), 1):
        determination = finding["determination"]
        group = determination if status == "completed" and determination != "uncertain" else "unresolved"
        groups[group].append((index, issue, finding))
    coverage = {True: "sufficient", False: "insufficient", None: "not assessed"}[verdict["coverage_sufficient"]]
    try:
        validate_assessment_report(
            report, directory, static_only=report.get("metadata", {}).get("llm_requested") is False,
        )
        scanner_successful = True
    except (ScanError, KeyError, TypeError, AttributeError):
        scanner_successful = False
    native_coverage = report.get("analysis_completeness")
    complete = native_coverage.get("is_complete") if isinstance(native_coverage, dict) else None
    scanner_coverage = "complete" if complete is True else "partial" if complete is False else "not reported"
    confirmed = len(groups["true_positive"])
    remediation = "finding requires" if confirmed == 1 else "findings require"
    lines = [
        f"**{confirmed} confirmed {remediation} remediation.**",
        "", markdown(verdict["summary"]), "", f"Scope: {markdown(verdict['scope'])}",
    ]
    if not scanner_successful:
        lines.extend(["", "**Scanner execution failed or requested analysis was unavailable or degraded.**"])
    if status != "completed" or verdict["coverage_sufficient"] is not True or not scanner_successful:
        lines.extend(["", "**Safety is not established by this assessment.**"])
    lines.extend([
        "", "| Assessment | Result |", "| --- | --- |",
        f"| Unresolved findings | {len(groups['unresolved'])} |",
        f"| False positives | {len(groups['false_positive'])} |",
        f"| Adjudication | {markdown(status)} |",
        f"| Coverage judgment | {coverage} |",
        f"| Scanner-reported coverage | {scanner_coverage} |",
        "", f"Limitations and coverage rationale: {markdown(verdict['coverage_reason'])}",
    ])
    for group, heading in (
        ("true_positive", "Requires remediation"), ("unresolved", "Unresolved"), ("false_positive", "False positives"),
    ):
        if not groups[group]:
            continue
        lines.extend(["", f"## {heading}"])
        for index, issue, finding in groups[group]:
            location = issue.get("location") or {}
            where = location.get("file") or "Location not recorded"
            if location.get("start_line") is not None:
                where += f":{location['start_line']}"
            context = markdown(where)
            reason = markdown(finding["reason"])
            if group == "false_positive":
                lines.extend(["", f"- {context}: {reason}"])
                continue
            title = issue.get("pattern") or issue.get("id", issue.get("rule_id")) or f"Finding {index}"
            lines.extend([
                "", f"- **{index}. {markdown(title)}** — {context}",
                f"  - Determination: {markdown(finding['determination'])}. Reason: {reason}",
                f"  - Finding: {markdown(issue.get('finding') or issue.get('explanation') or 'Not recorded')}",
            ])
            if issue.get("explanation") and issue.get("finding"):
                lines.append(f"  - Explanation: {markdown(issue['explanation'])}")
            if issue.get("remediation"):
                lines.append(f"  - Remediation: {markdown(issue['remediation'])}")
    return "\n".join(lines) + "\n"


def register(subparsers) -> None:
    parser = subparsers.add_parser(
        "summarize", help="Summarize required remediation, unresolved findings, and false positives.",
    )
    parser.add_argument("--assessment-dir", type=Path, required=True)
    parser.set_defaults(handler=run)


def run(args) -> int:
    try:
        output = summarize(args.assessment_dir)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, ScanError) as exc:
        print(f"Cannot summarize assessment: {exc}", file=sys.stderr)
        return 1
    print(output, end="")
    return 0
