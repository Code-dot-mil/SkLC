"""Assemble the prebuilt site release without building or assessing its inputs."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import tempfile
import zipfile
from email.parser import Parser
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


def _stage_deployment_kit(repo_root: Path, site_dir: Path, stage_root: Path) -> None:
    shutil.copytree(site_dir, stage_root / "public")
    (stage_root / "public" / ".gitkeep").unlink(missing_ok=True)
    product = repo_root / "products" / "deployment-kit"
    docs = product / "docs" / "prebuilt"
    shutil.copy2(product / "ci" / "gitlab" / "prebuilt" / ".gitlab-ci.yml", stage_root / ".gitlab-ci.yml")
    shutil.copy2(docs / "README.md", stage_root / "README.md")
    (stage_root / "docs").mkdir()
    for name in ("install.md", "deploy-gitlab-pages.md", "deploy-static-hosting.md"):
        shutil.copy2(docs / name, stage_root / "docs" / name)


def build_release(
    *,
    repo_root: Path,
    site_dir: Path,
    output_dir: Path,
    version: str,
) -> Path:
    """Package the built site and deployment guides as one ZIP."""
    validate_version(version)
    package_name = f"deployment-kit-prebuilt-{version}"
    with tempfile.TemporaryDirectory(prefix="sklc-prebuilt-") as temporary:
        package_root = Path(temporary) / package_name
        _stage_deployment_kit(repo_root, site_dir, package_root)
        output_dir.mkdir(parents=True, exist_ok=True)
        return Path(shutil.make_archive(str(output_dir / package_name), "zip", root_dir=package_root))


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


def validate_wheel_name(name: str, version: str) -> None:
    """Require the assessment product and a Python-normalized release version."""
    from packaging.utils import parse_wheel_filename
    from packaging.version import Version

    try:
        distribution, wheel_version, _build, _tags = parse_wheel_filename(name)
        if distribution != "skill-assessment" or wheel_version != Version(version):
            raise ValueError("assessment package and release versions must correspond")
    except ValueError as error:
        raise ReleaseError("invalid assessment wheel name or release version") from error


def check_wheel(wheel: Path, version: str) -> None:
    """Check a built wheel's filename and packaged distribution metadata."""
    from packaging.utils import canonicalize_name
    from packaging.version import Version

    validate_version(version)
    validate_wheel_name(wheel.name, version)
    if wheel.is_symlink() or not wheel.is_file():
        raise ReleaseError("assessment wheel must be a regular file")
    try:
        with zipfile.ZipFile(wheel) as archive:
            metadata_paths = [name for name in archive.namelist() if name.endswith(".dist-info/METADATA")]
            if len(metadata_paths) != 1:
                raise ValueError("expected one distribution metadata file")
            metadata = Parser().parsestr(archive.read(metadata_paths[0]).decode("utf-8"))
        if (canonicalize_name(metadata["Name"] or "") != "skill-assessment"
                or Version(metadata["Version"] or "") != Version(version)):
            raise ValueError("packaged assessment version does not match the release")
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        raise ReleaseError("assessment wheel metadata does not match the release") from error


def _draft_asset_digests(assets: list[GitReleaseAsset], version: str) -> dict[str, str]:
    """Require two product ZIPs and the assessment wheel with GitHub digests."""
    expected_assets = {f"deployment-kit-prebuilt-{version}.zip", f"skill-catalog-{version}.zip"}
    wheels = [asset.name for asset in assets if asset.name.endswith(".whl")]
    if len(assets) != 3 or len(wheels) != 1 or {asset.name for asset in assets} != expected_assets | set(wheels):
        raise ReleaseError("draft must contain exactly two versioned product ZIPs and the assessment wheel")
    validate_wheel_name(wheels[0], version)
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
    parser = argparse.ArgumentParser(description="Check release readiness and assemble release packages")
    commands = parser.add_subparsers(dest="command", required=True)
    for command, help_text in (
        ("build", "package an already-built site as a ZIP"),
        ("stage", "stage package contents for a CI artifact upload"),
    ):
        package = commands.add_parser(command, help=help_text)
        if command == "build":
            package.add_argument("--version", required=True)
        package.add_argument("--repo-root", type=Path, default=Path.cwd())
        package.add_argument("--site-dir", type=Path, default=Path("site/dist"))
        package.add_argument("--output-dir", type=Path, required=True)
    validate = commands.add_parser("validate-version", help="validate a SemVer release version without a leading v")
    validate.add_argument("--version", required=True)
    wheel = commands.add_parser("check-wheel", help="verify assessment wheel identity and release version")
    wheel.add_argument("--wheel", type=Path, required=True)
    wheel.add_argument("--version", required=True)
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
    if args.command == "check-wheel":
        try:
            check_wheel(args.wheel, args.version)
        except ReleaseError as error:
            parser.exit(1, f"Release blocked: {error}\n")
        return
    if args.command == "validate-version":
        validate_version(args.version)
        return
    if args.command == "release-notes":
        snippet = extract_release_notes(args.notes_file, args.version)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(snippet, encoding="utf-8", newline="\n")
        return
    repo_root = args.repo_root.absolute()
    site_dir = args.site_dir if args.site_dir.is_absolute() else repo_root / args.site_dir
    if args.command == "stage":
        _stage_deployment_kit(repo_root, site_dir, args.output_dir.absolute())
        return
    built = build_release(
        repo_root=repo_root,
        site_dir=site_dir,
        output_dir=args.output_dir.absolute(),
        version=args.version,
    )
    print(json.dumps({"artifacts": [str(built)]}, indent=2))


if __name__ == "__main__":
    main()
