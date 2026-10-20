"""Verify release readiness, notes, and the existing GitHub draft."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from github.GitReleaseAsset import GitReleaseAsset

SEMVER_PATTERN = re.compile(
    r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-(?:0|[1-9][0-9]*|[0-9A-Za-z-]*[A-Za-z-][0-9A-Za-z-]*)"
    r"(?:\.(?:0|[1-9][0-9]*|[0-9A-Za-z-]*[A-Za-z-][0-9A-Za-z-]*))*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
)


RELEASE_REPOSITORY = "Code-dot-mil/SkLC"


class ReleaseError(ValueError):
    pass


def validate_version(version: str) -> None:
    if not SEMVER_PATTERN.fullmatch(version):
        raise ReleaseError(f"version must be a SemVer value without a leading v: {version}")


def extract_release_notes(notes_path: Path, version: str) -> str:
    """Select exactly one nonempty version section, ignoring fenced examples."""
    validate_version(version)
    if not notes_path.is_file():
        raise ReleaseError(f"release notes file is missing: {notes_path}")
    lines = notes_path.read_text(encoding="utf-8").splitlines()
    headings: list[tuple[int, str, str]] = []
    fence: str | None = None
    for index, line in enumerate(lines):
        if fence is not None:
            if re.fullmatch(rf" {{0,3}}{fence[0]}{{{len(fence)},}}[ \t]*", line):
                fence = None
            continue
        opening = re.match(r" {0,3}(`{3,}|~{3,})", line)
        if opening:
            fence = opening[1]
            continue
        heading = re.match(r" {0,3}(#{1,2})[ \t]+", line)
        if heading and (title := line[heading.end():].rstrip(" \t")):
            headings.append((index, heading[1], title))
    matches = [index for index, level, title in headings if level == "##" and title == version]
    if len(matches) != 1:
        raise ReleaseError(f"release notes must contain exactly one heading '## {version}'")
    start = matches[0]
    end = next((index for index, _level, _title in headings if index > start), len(lines))
    if not "\n".join(lines[start + 1:end]).strip():
        raise ReleaseError(f"release notes section for {version} is empty")
    return "\n".join(lines[start:end]).strip() + "\n"


def _check_candidate(*, version: str, expected_commit: str, unused_tag: bool) -> tuple[str, str, str]:
    """Verify the checkout and notes shared by both release stages."""
    import pygit2

    validate_version(version)
    if not re.fullmatch(r"[0-9a-fA-F]{40}", expected_commit):
        raise ReleaseError("expected commit must be the full 40-character SHA selected from GitHub")
    sha = expected_commit.lower()
    try:
        git_dir = pygit2.discover_repository(str(Path.cwd()))
        if git_dir is None:
            raise ReleaseError("run from the candidate Git checkout")
        local = pygit2.Repository(git_dir)
        if local.is_bare or local.head_is_unborn:
            raise ReleaseError("a working checkout with a committed HEAD is required")
        if str(local.head.target) != sha:
            raise ReleaseError(f"local HEAD {local.head.target} does not match expected commit {sha}")
        if local.status(untracked_files="all"):
            raise ReleaseError("checkout must be clean, including staged and untracked files")
        if local.state() != pygit2.enums.RepositoryState.NONE:
            raise ReleaseError("finish the in-progress Git operation before checking readiness")
        tag = f"v{version}"
        if unused_tag and f"refs/tags/{tag}" in local.references:
            raise ReleaseError(f"local tag {tag} already exists")
        notes = extract_release_notes(Path(local.workdir) / "RELEASE_NOTES.md", version)
    except (pygit2.GitError, OSError) as error:
        raise ReleaseError(f"cannot verify local checkout: {error}") from error
    return sha, tag, notes


def _github_token() -> str:
    """Require authentication so checks include drafts visible to the maintainer."""

    # A token is required so private/draft release visibility is not silently omitted.
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise ReleaseError("set GH_TOKEN (or GITHUB_TOKEN) with repository and Actions read access")
    return token


def check_ready(*, version: str, expected_commit: str) -> dict[str, str]:
    """Require an unused version and successful main CI before pushing a tag."""
    from github import Auth, Github, GithubException, UnknownObjectException
    from requests.exceptions import RequestException

    sha, tag, _notes = _check_candidate(version=version, expected_commit=expected_commit, unused_tag=True)
    token = _github_token()
    try:
        with Github(auth=Auth.Token(token), timeout=30) as client:
            remote = client.get_repo(RELEASE_REPOSITORY)
            if remote.compare(sha, "main").status not in {"ahead", "identical"}:
                raise ReleaseError(f"candidate {sha} is not on {RELEASE_REPOSITORY} main history")
            try:
                remote.get_git_ref(f"tags/{tag}")
            except UnknownObjectException:
                pass
            else:
                raise ReleaseError(f"GitHub tag {tag} already exists")
            # Include drafts visible to this identity, which tag-based release lookup can omit.
            if any(release.tag_name == tag for release in remote.get_releases()):
                raise ReleaseError(f"GitHub release {tag} already exists")
            workflow = remote.get_workflow("ci.yml")
            run = next(iter(workflow.get_runs(branch="main", event="push", head_sha=sha)), None)
            if run is None:
                raise ReleaseError(f"no main push CI run exists for {sha}")
            if run.status != "completed" or run.conclusion != "success":
                raise ReleaseError(f"CI is {run.status}/{run.conclusion}: {run.html_url}")
            return {"version": version, "tag": tag, "candidate_sha": sha, "ci_url": run.html_url}
    except GithubException as error:
        raise ReleaseError(f"GitHub verification failed (HTTP {error.status}); readiness is unverified") from error
    except RequestException as error:
        raise ReleaseError("GitHub request failed; readiness is unverified") from error


def _draft_asset_digests(assets: list[GitReleaseAsset], version: str) -> dict[str, str]:
    """Require three product ZIPs and the assessment wheel with GitHub digests."""
    expected_assets = {f"deployment-kit-{mode}-{version}.zip" for mode in ("prebuilt", "operator")}
    expected_assets.add(f"skill-catalog-{version}.zip")
    wheels = [
        asset.name for asset in assets
        if asset.name.startswith("skill_assessment-") and asset.name.endswith(".whl")
    ]
    if len(assets) != 4 or len(wheels) != 1 or {asset.name for asset in assets} != expected_assets | set(wheels):
        raise ReleaseError("draft must contain exactly three versioned product ZIPs and the assessment wheel")
    for asset in assets:
        if asset.state != "uploaded" or asset.size <= 0:
            raise ReleaseError(f"draft asset is incomplete: {asset.name}")
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", asset.digest or ""):
            raise ReleaseError(f"draft asset has no valid GitHub SHA-256 digest: {asset.name}")
    return {asset.name: asset.digest for asset in assets}


def check_draft(*, version: str, expected_commit: str) -> dict[str, object]:
    """Verify the workflow-prepared draft before publishing the existing release."""
    from github import Auth, Github, GithubException
    from requests.exceptions import RequestException

    sha, tag, notes = _check_candidate(version=version, expected_commit=expected_commit, unused_tag=False)
    token = _github_token()
    try:
        with Github(auth=Auth.Token(token), timeout=30) as client:
            remote = client.get_repo(RELEASE_REPOSITORY)
            if remote.compare(sha, "main").status not in {"ahead", "identical"}:
                raise ReleaseError(f"candidate {sha} is not on {RELEASE_REPOSITORY} main history")
            target = remote.get_git_ref(f"tags/{tag}").object
            while target.type == "tag":
                target = remote.get_git_tag(target.sha).object
            if target.type != "commit" or target.sha != sha:
                raise ReleaseError(f"GitHub tag {tag} does not target candidate {sha}")
            release = next((release for release in remote.get_releases() if release.tag_name == tag), None)
            if release is None:
                raise ReleaseError(f"no draft exists for {tag}; wait for the release workflow")
            if not release.draft:
                raise ReleaseError(f"GitHub release {tag} is already published: {release.html_url}")
            if (release.body or "").strip() != notes.strip():
                raise ReleaseError(f"draft release notes do not match the committed {version} section")
            if release.prerelease != ("-" in version.split("+", 1)[0]):
                raise ReleaseError(f"draft prerelease status does not match version {version}")
            digests = _draft_asset_digests(list(release.get_assets()), version)
            workflow = remote.get_workflow("release.yml")
            run = next(iter(workflow.get_runs(branch=tag, event="push", head_sha=sha)), None)
            if run is None:
                raise ReleaseError(f"no release workflow run exists for {tag} at {sha}")
            if run.status != "completed" or run.conclusion != "success":
                raise ReleaseError(f"release workflow is {run.status}/{run.conclusion}: {run.html_url}")
            return {
                "version": version, "tag": tag, "candidate_sha": sha,
                "release_url": release.html_url, "workflow_url": run.html_url,
                "assets": digests,
            }
    except GithubException as error:
        raise ReleaseError(f"GitHub verification failed (HTTP {error.status}); draft is unverified") from error
    except RequestException as error:
        raise ReleaseError("GitHub request failed; draft is unverified") from error


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify release readiness, notes, and drafts")
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate-version", help="validate a SemVer release version without a leading v")
    validate.add_argument("--version", required=True)
    notes = commands.add_parser("release-notes", help="extract one accepted version section")
    notes.add_argument("--version", required=True)
    notes.add_argument("--notes-file", type=Path, default=Path("RELEASE_NOTES.md"))
    notes.add_argument("--output", type=Path, required=True)
    for command, help_text in (
        ("check-ready", "verify an unused version and candidate before pushing a release tag"),
        ("check-draft", "verify the existing draft, tag, assets, and successful release workflow before publishing"),
    ):
        check = commands.add_parser(command, help=help_text)
        check.add_argument("--version", required=True)
        check.add_argument("--expected-commit", required=True)
    args = parser.parse_args()
    if args.command in {"check-ready", "check-draft"}:
        try:
            check = check_ready if args.command == "check-ready" else check_draft
            result = check(version=args.version, expected_commit=args.expected_commit)
        except ReleaseError as error:
            parser.exit(1, f"Release blocked: {error}\n")
        print(json.dumps(result, indent=2))
        return
    if args.command == "validate-version":
        validate_version(args.version)
        return
    if args.command == "release-notes":
        snippet = extract_release_notes(args.notes_file, args.version)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(snippet, encoding="utf-8", newline="\n")
        return


if __name__ == "__main__":
    main()
