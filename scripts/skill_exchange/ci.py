from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from .exchange_builder import build_exchange
from .policy import load_exchange_policy
from .risk import assess_report
from .skills import discover_skills
from .skillspector import run_skillspector
from .validation import validate_skill

SCAN_MODES = ("static-only", "llm-assisted")


def main() -> None:
    parser = argparse.ArgumentParser(description="GitLab CI helpers for the static skill exchange.")
    subcommands = parser.add_subparsers(dest="command", required=True)

    review = subcommands.add_parser("review")
    review.add_argument("--base-ref")
    review.add_argument("--head-ref")
    review.add_argument("--repo-root", type=Path, default=Path("."))
    review.add_argument("--skills-root", type=Path, default=Path("skills"))
    review.add_argument("--exchange-dir", type=Path, default=Path(".exchange"))
    review.add_argument("--artifacts-dir", type=Path, default=Path("review-artifacts"))
    review.add_argument(
        "--scan-mode",
        choices=SCAN_MODES,
        default=os.environ.get("SKILL_EXCHANGE_REVIEW_SCAN_MODE", "static-only"),
    )
    review.add_argument("--post-comment", action="store_true", default=env_flag("SKILL_EXCHANGE_POST_REVIEW_COMMENT"))

    publish = subcommands.add_parser("publish")
    publish.add_argument("--repo-root", type=Path, default=Path("."))
    publish.add_argument("--skills-root", type=Path, default=Path("skills"))
    publish.add_argument("--exchange-dir", type=Path, default=Path(".exchange"))
    publish.add_argument("--generated-dir", type=Path, default=Path(".exchange/generated"))
    publish.add_argument("--scan-modes", default=os.environ.get("SKILL_EXCHANGE_PUBLISH_SCAN_MODES", "static-only"))
    publish.add_argument("--result-path", type=Path, default=Path("publish-result.json"))
    publish.add_argument("--commit-generated", action="store_true", default=env_flag("EXCHANGE_PUBLISH_COMMIT"))

    args = parser.parse_args()
    if args.command == "review":
        run_review_command(args)
    if args.command == "publish":
        run_publish_command(args)


def run_review_command(args: argparse.Namespace) -> None:
    repo_root = args.repo_root.resolve()
    base_ref = args.base_ref or env_value("SKILL_EXCHANGE_DIFF_BASE") or env_value("CI_MERGE_REQUEST_DIFF_BASE_SHA")
    head_ref = args.head_ref or env_value("SKILL_EXCHANGE_DIFF_HEAD") or env_value("CI_COMMIT_SHA") or "HEAD"
    if not base_ref:
        base_ref = resolve_default_base_ref(head_ref, repo_root)

    changed_skill_paths = changed_skill_paths_from_git(
        base_ref=base_ref,
        head_ref=head_ref,
        repo_root=repo_root,
        skills_root=args.skills_root,
    )
    result = review_changed_skills(
        changed_skill_paths=changed_skill_paths,
        repo_root=repo_root,
        exchange_dir=resolve_repo_path(repo_root, args.exchange_dir),
        artifacts_dir=resolve_repo_path(repo_root, args.artifacts_dir),
        scan_mode=args.scan_mode,
        post_comment=args.post_comment,
        skills_root=args.skills_root,
    )
    print(json.dumps(result, indent=2, sort_keys=True))

    if result["validation_errors"] and env_flag("SKILL_EXCHANGE_REVIEW_FAIL_ON_VALIDATION_ERRORS", default=True):
        raise SystemExit(1)
    if result["scanner_errors"] and env_flag("SKILL_EXCHANGE_REVIEW_FAIL_ON_SCANNER_ERROR"):
        raise SystemExit(1)


def run_publish_command(args: argparse.Namespace) -> None:
    repo_root = args.repo_root.resolve()
    result = build_exchange(
        skills_root=resolve_repo_path(repo_root, args.skills_root),
        exchange_dir=resolve_repo_path(repo_root, args.exchange_dir),
        generated_dir=resolve_repo_path(repo_root, args.generated_dir),
        scan_modes=parse_scan_modes(args.scan_modes),
    )
    result_path = resolve_repo_path(repo_root, args.result_path)
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))

    if args.commit_generated:
        commit_result = commit_generated_outputs(
            repo_root=repo_root,
            generated_dir=resolve_repo_path(repo_root, args.generated_dir),
        )
        print(json.dumps(commit_result, indent=2, sort_keys=True))


def parse_scan_modes(value: str | None) -> tuple[str, ...]:
    if not value:
        return ("static-only",)
    modes = tuple(part for part in re.split(r"[\s,]+", value.strip()) if part)
    unsupported = sorted(set(modes) - set(SCAN_MODES))
    if unsupported:
        raise ValueError(f"unsupported scan mode(s): {', '.join(unsupported)}")
    return modes or ("static-only",)


def changed_skill_paths_from_git(
    *,
    base_ref: str,
    head_ref: str,
    repo_root: Path,
    skills_root: Path = Path("skills"),
) -> list[Path]:
    completed = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            "--diff-filter=ACMRT",
            base_ref,
            head_ref,
            "--",
            skills_root.as_posix(),
        ],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "git diff failed")
    return changed_skill_paths_from_names(completed.stdout.splitlines(), repo_root=repo_root, skills_root=skills_root)


def changed_skill_paths_from_names(
    changed_names: list[str],
    *,
    repo_root: Path,
    skills_root: Path = Path("skills"),
) -> list[Path]:
    roots: set[Path] = set()
    root_parts = skills_root.parts
    for changed_name in changed_names:
        path = Path(changed_name)
        parts = path.parts
        if len(parts) < len(root_parts) + 2:
            continue
        if parts[: len(root_parts)] != root_parts:
            continue
        roots.add(repo_root / Path(*parts[: len(root_parts) + 2]))
    return sorted(roots, key=lambda item: item.as_posix())


def review_changed_skills(
    *,
    changed_skill_paths: list[Path],
    repo_root: Path,
    exchange_dir: Path,
    artifacts_dir: Path,
    scan_mode: str,
    post_comment: bool,
    skills_root: Path = Path("skills"),
) -> dict[str, Any]:
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    policy = load_exchange_policy(exchange_dir)
    skills_by_path = {
        skill.path.resolve(): skill
        for skill in discover_skills(resolve_repo_path(repo_root, skills_root))
    }

    validation_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    validation_errors = 0
    scanner_errors = 0

    for skill_path in changed_skill_paths:
        resolved_skill_path = skill_path.resolve()
        skill = skills_by_path.get(resolved_skill_path)
        if skill is None:
            validation_errors += 1
            validation_rows.append(
                {
                    "skill": skill_display_id_from_path(repo_root, resolved_skill_path),
                    "path": relative_to_repo(repo_root, resolved_skill_path),
                    "errors": ["missing SKILL.md"],
                    "warnings": [],
                    "metadata_flags": [],
                }
            )
            continue

        validation = validate_skill(skill, policy)
        validation_errors += len(validation.errors)
        validation_rows.append(
            {
                "skill": skill.metadata.display_id,
                "path": relative_to_repo(repo_root, skill.path),
                "errors": list(validation.errors),
                "warnings": list(validation.warnings),
                "metadata_flags": list(validation.metadata_flags),
            }
        )

        report_path = (
            artifacts_dir
            / "skillspector"
            / skill.metadata.namespace
            / skill.metadata.skill_id
            / "report.json"
        )
        scanner_error = None
        scanner_findings: list[dict[str, str]] = []
        try:
            report = run_skillspector(skill.path, report_path, no_llm=scan_mode == "static-only")
            assessment = assess_report(report)
            scanner_findings = scanner_findings_from_report(report)
        except Exception as exc:
            scanner_errors += 1
            scanner_error = str(exc)
            assessment = {
                "risk": "Unknown",
                "reason": f"scanner_failed: {scanner_error}",
                "confidence_flags": [],
            }

        summary_rows.append(
            {
                "skill": skill.metadata.display_id,
                "risk": assessment["risk"],
                "reason": assessment["reason"],
                "confidence_flags": list(assessment["confidence_flags"]),
                "scan_mode": scan_mode,
                "report": str(report_path),
                "scanner_error": scanner_error,
                "scanner_findings": scanner_findings,
            }
        )

    write_json(artifacts_dir / "validation.json", validation_rows)
    write_json(artifacts_dir / "changed-skills.json", summary_rows)
    comment = render_review_comment(summary_rows, validation_rows)
    (artifacts_dir / "comment.md").write_text(comment)
    comment_status = post_review_comment(comment) if post_comment else "disabled"
    result = {
        "reviewed_skills": len(summary_rows),
        "changed_skill_paths": [relative_to_repo(repo_root, path) for path in changed_skill_paths],
        "validation_errors": validation_errors,
        "scanner_errors": scanner_errors,
        "comment_status": comment_status,
    }
    write_json(artifacts_dir / "result.json", result)
    return result


def render_review_comment(summary_rows: list[dict[str, Any]], validation_rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Skill Exchange Review",
        "",
        "| Skill | Risk | Flags | Scan mode | Reason |",
        "|---|---|---|---|---|",
    ]
    if not summary_rows:
        lines.append("| - | - | - | - | No changed skill packages were detected. |")
    for row in summary_rows:
        flags = ", ".join(row["confidence_flags"]) if row["confidence_flags"] else "-"
        lines.append(f"| `{row['skill']}` | {row['risk']} | {flags} | {row['scan_mode']} | {row['reason']} |")

    lines.extend(["", "## Scanner findings"])
    if not summary_rows:
        lines.append("- No changed skill packages were detected.")
    for row in summary_rows:
        lines.append(f"### `{row['skill']}`")
        if row.get("scanner_error"):
            lines.append(f"- Scanner failed: {row['scanner_error']}")
            continue

        findings = row.get("scanner_findings") or []
        if not findings:
            lines.append("- No scanner findings were reported.")
            continue

        for index, finding in enumerate(findings, start=1):
            title = scanner_finding_title(finding)
            lines.append(f"{index}. **{finding['severity']}** `{finding['id']}` - {title}")
            if finding["location"]:
                lines.append(f"   - Location: `{finding['location']}`")
            if finding["confidence"]:
                lines.append(f"   - Confidence: {finding['confidence']}")
            if finding["finding"]:
                lines.append(f"   - Finding: {finding['finding']}")
            if finding["explanation"]:
                lines.append(f"   - Explanation: {finding['explanation']}")
            if finding["remediation"]:
                lines.append(f"   - Remediation: {finding['remediation']}")
            if finding["code_snippet"]:
                lines.append("   - Snippet:")
                lines.extend(indented_code_block(finding["code_snippet"]))

    lines.extend(["", "## Exchange validation"])
    if not validation_rows:
        lines.append("- No changed skill packages were detected.")
    for row in validation_rows:
        errors = ", ".join(row["errors"]) if row["errors"] else "none"
        warnings = ", ".join(row["warnings"]) if row["warnings"] else "none"
        flags = ", ".join(row["metadata_flags"]) if row["metadata_flags"] else "none"
        lines.append(f"- `{row['skill']}` errors: {errors}; warnings: {warnings}; metadata flags: {flags}")
    return "\n".join(lines) + "\n"


def scanner_findings_from_report(report: dict[str, Any]) -> list[dict[str, str]]:
    issues = report.get("issues")
    if not isinstance(issues, list):
        return []

    findings: list[dict[str, str]] = []
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        location = issue.get("location") if isinstance(issue.get("location"), dict) else {}
        findings.append(
            {
                "id": one_line(issue.get("id")) or "unknown",
                "severity": (one_line(issue.get("severity")) or "UNKNOWN").upper(),
                "category": one_line(issue.get("category")),
                "pattern": one_line(issue.get("pattern")),
                "location": scanner_issue_location(location),
                "confidence": one_line(issue.get("confidence")),
                "finding": one_line(issue.get("finding")),
                "explanation": one_line(issue.get("explanation")),
                "remediation": one_line(issue.get("remediation")),
                "code_snippet": str(issue.get("code_snippet") or "").strip(),
            }
        )
    return findings


def scanner_finding_title(finding: dict[str, str]) -> str:
    parts = [finding["category"], finding["pattern"]]
    return " / ".join(part for part in parts if part) or "Untitled finding"


def scanner_issue_location(location: dict[str, Any]) -> str:
    file = one_line(location.get("file"))
    start_line = one_line(location.get("start_line"))
    end_line = one_line(location.get("end_line"))
    if not file:
        return ""
    if start_line and end_line and end_line != start_line:
        return f"{file}:{start_line}-{end_line}"
    if start_line:
        return f"{file}:{start_line}"
    return file


def indented_code_block(value: str) -> list[str]:
    lines = ["     ```text"]
    lines.extend(f"     {line}" for line in value.replace("```", "'''").splitlines())
    lines.append("     ```")
    return lines


def one_line(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def post_review_comment(body: str) -> str:
    token_variable = os.environ.get("SKILL_EXCHANGE_REVIEW_TOKEN_VARIABLE", "GITLAB_TOKEN")
    token = os.environ.get(token_variable)
    api_url = os.environ.get("CI_API_V4_URL")
    project_id = os.environ.get("CI_PROJECT_ID")
    mr_iid = os.environ.get("CI_MERGE_REQUEST_IID")
    if not token:
        return f"skipped: {token_variable} is not set"
    if not api_url or not project_id or not mr_iid:
        return "skipped: GitLab merge request environment is incomplete"

    token_header = os.environ.get("SKILL_EXCHANGE_REVIEW_TOKEN_HEADER")
    if not token_header:
        token_header = "JOB-TOKEN" if token_variable == "CI_JOB_TOKEN" else "PRIVATE-TOKEN"
    route = (
        f"{api_url.rstrip('/')}/projects/{urllib.parse.quote(project_id, safe='')}"
        f"/merge_requests/{urllib.parse.quote(mr_iid, safe='')}/notes"
    )
    payload = urllib.parse.urlencode({"body": body}).encode()
    request = urllib.request.Request(route, data=payload, headers={token_header: token})
    with urllib.request.urlopen(request, timeout=30) as response:
        return f"posted: HTTP {response.status}"


def commit_generated_outputs(*, repo_root: Path, generated_dir: Path) -> dict[str, Any]:
    boe_dir = generated_dir / "boe"
    if not boe_dir.exists():
        return {"committed": False, "pushed": False, "reason": "no BOE generated"}

    relative_generated_dir = relative_to_repo(repo_root, boe_dir)
    run_git(repo_root, "config", "user.name", os.environ.get("EXCHANGE_BOT_GIT_NAME", "skill-exchange-bot"))
    run_git(
        repo_root,
        "config",
        "user.email",
        os.environ.get("EXCHANGE_BOT_GIT_EMAIL", "skill-exchange-bot@example.invalid"),
    )
    run_git(repo_root, "add", "-f", "--", relative_generated_dir)

    diff = subprocess.run(
        ["git", "diff", "--cached", "--quiet", "--", relative_generated_dir],
        cwd=repo_root,
        check=False,
    )
    if diff.returncode == 0:
        return {"committed": False, "pushed": False, "reason": "no generated changes"}

    message = os.environ.get("EXCHANGE_PUBLISH_COMMIT_MESSAGE", "chore: update generated exchange evidence")
    run_git(repo_root, "commit", "-m", message)
    pushed = False
    if env_flag("EXCHANGE_PUBLISH_PUSH", default=True):
        configure_push_remote(repo_root)
        branch = os.environ.get("EXCHANGE_PUBLISH_BRANCH") or os.environ.get("CI_DEFAULT_BRANCH", "main")
        run_git(repo_root, "push", "origin", f"HEAD:{branch}")
        pushed = True
    return {"committed": True, "pushed": pushed, "path": relative_generated_dir}


def configure_push_remote(repo_root: Path) -> None:
    push_url = os.environ.get("EXCHANGE_PUBLISH_PUSH_URL")
    if not push_url:
        token = os.environ.get("EXCHANGE_PUBLISH_TOKEN") or os.environ.get("GITLAB_TOKEN")
        username = os.environ.get("EXCHANGE_PUBLISH_USERNAME")
        if not token and os.environ.get("CI_JOB_TOKEN"):
            token = os.environ["CI_JOB_TOKEN"]
            username = username or "gitlab-ci-token"
        username = username or "oauth2"
        protocol = os.environ.get("CI_SERVER_PROTOCOL", "https")
        host = os.environ.get("CI_SERVER_HOST")
        project_path = os.environ.get("CI_PROJECT_PATH")
        if not token or not host or not project_path:
            raise RuntimeError(
                "set EXCHANGE_PUBLISH_PUSH_URL, or set EXCHANGE_PUBLISH_TOKEN with CI_SERVER_HOST and CI_PROJECT_PATH"
            )
        push_url = (
            f"{protocol}://{urllib.parse.quote(username, safe='')}:"
            f"{urllib.parse.quote(token, safe='')}@{host}/{project_path}.git"
        )
    run_git(repo_root, "remote", "set-url", "origin", push_url)


def resolve_default_base_ref(head_ref: str, repo_root: Path) -> str:
    target_branch = (
        os.environ.get("CI_MERGE_REQUEST_TARGET_BRANCH_NAME")
        or os.environ.get("CI_DEFAULT_BRANCH")
        or "main"
    )
    remote_ref = f"origin/{target_branch}"
    fetch = subprocess.run(
        ["git", "fetch", "--quiet", "origin", f"{target_branch}:refs/remotes/{remote_ref}"],
        cwd=repo_root,
        check=False,
    )
    if fetch.returncode != 0:
        remote_ref = target_branch
    completed = subprocess.run(
        ["git", "merge-base", remote_ref, head_ref],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "could not resolve diff base")
    return completed.stdout.strip()


def resolve_repo_path(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


def relative_to_repo(repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def skill_display_id_from_path(repo_root: Path, skill_path: Path) -> str:
    rel = Path(relative_to_repo(repo_root, skill_path))
    if len(rel.parts) >= 3 and rel.parts[0] == "skills":
        return f"{rel.parts[1]}/{rel.parts[2]}"
    return rel.as_posix()


def env_flag(name: str, *, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_value(name: str) -> str | None:
    value = os.environ.get(name)
    if value and value != "0000000000000000000000000000000000000000":
        return value
    return None


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def run_git(repo_root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=repo_root, check=True)


if __name__ == "__main__":
    main()
