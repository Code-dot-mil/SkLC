from pathlib import Path

import pytest
from sklc_maintainer.release import ReleaseError, extract_release_notes, validate_version

VERSION = "1.2.3"


def _write(path: Path, content: bytes) -> None:
    path.write_bytes(content)


@pytest.mark.parametrize("version", [VERSION, "1.2.3-rc.1+build.7"])
@pytest.mark.parametrize("fence", ["```", "~~~~"])
def test_release_notes_select_exact_version_and_preserve_subsections(tmp_path: Path, version: str, fence: str):
    notes = tmp_path / "RELEASE_NOTES.md"
    accepted = f"## {version}\n\n- Portable prebuilt download.\n\n### Compatibility\n\n- Portable static hosting.\n"
    _write(notes, (
        f"# Release Notes\n\n{fence}markdown\n## {version}\nExample only.\n{fence}\n\n"
        f"## 9.0.0\n\nLater release.\n\n{accepted}\n## 0.1.0\n\nEarlier release.\n"
    ).encode())

    assert extract_release_notes(notes, version) == accepted


@pytest.mark.parametrize("contents,error", [
    ("# Release Notes\n", "exactly one heading"),
    ("## 1.2.30\nWrong version.\n", "exactly one heading"),
    ("## 1.2.3\nFirst.\n## 1.2.3\nSecond.\n", "exactly one heading"),
    ("## 1.2.3\n\n## 1.0.0\nOld notes.\n", "empty"),
    ("## 1.2.3\n \t\n", "empty"),
    ("````markdown\n```\n## 1.2.3\nExample only.\n````\n", "exactly one heading"),
])
def test_release_notes_reject_missing_ambiguous_or_empty_sections(tmp_path: Path, contents: str, error: str):
    notes = tmp_path / "RELEASE_NOTES.md"
    _write(notes, contents.encode())

    with pytest.raises(ReleaseError, match=error):
        extract_release_notes(notes, VERSION)


def test_release_notes_reject_missing_file(tmp_path: Path):
    with pytest.raises(ReleaseError, match="missing"):
        extract_release_notes(tmp_path / "RELEASE_NOTES.md", VERSION)


@pytest.mark.parametrize("version", ["../escape", "v1.2.3", "1.2", "01.2.3", "1.2.3-01", "1.2.3\n"])
def test_release_version_rejects_invalid_semver(version: str):
    with pytest.raises(ReleaseError):
        validate_version(version)


@pytest.fixture
def release_candidate(tmp_path, monkeypatch):
    """Real local candidate; only GitHub responses are substituted."""
    import subprocess
    from contextlib import nullcontext
    from types import SimpleNamespace

    import github

    monkeypatch.chdir(tmp_path)
    def git(*args):
        return subprocess.check_output(["git", *args], text=True).strip()
    git("init", "-q")
    git("config", "user.name", "Release Test")
    git("config", "user.email", "release@example.invalid")
    notes = f"## {VERSION}\n\nA tested release.\n"
    (tmp_path / "RELEASE_NOTES.md").write_text(notes)
    git("add", ".")
    git("commit", "-qm", "Release candidate")
    sha = git("rev-parse", "HEAD")
    run = SimpleNamespace(status="completed", conclusion="success", html_url="https://example.invalid/run")
    assets = [SimpleNamespace(name=name, state="uploaded", size=100, digest="sha256:" + "a" * 64) for name in (
        f"deployment-kit-prebuilt-{VERSION}.zip", f"deployment-kit-operator-{VERSION}.zip",
        f"skill-bundle-{VERSION}.zip", f"skill-bundle-assessments-{VERSION}.zip",
        f"skill_assessment-{VERSION}-py3-none-any.whl",
    )]
    draft = SimpleNamespace(tag_name=f"v{VERSION}", draft=True, body=notes, prerelease=False,
                            html_url="https://example.invalid/release", get_assets=lambda: assets)
    state = SimpleNamespace(tag=None, releases=[], run=run, comparison="identical")
    def get_ref(ref):
        if ref != f"tags/v{VERSION}":
            raise AssertionError(ref)
        if state.tag is None:
            raise github.UnknownObjectException(404, {"message": "Not Found"})
        return SimpleNamespace(object=state.tag)
    def workflow(name):
        event_branch = "main" if name == "ci.yml" else f"v{VERSION}"
        return SimpleNamespace(get_runs=lambda **query: [state.run] if state.run is not None and query == {
            "branch": event_branch, "event": "push", "head_sha": sha,
        } else [])
    remote = SimpleNamespace(compare=lambda *_: SimpleNamespace(status=state.comparison),
                             get_git_ref=get_ref, get_releases=lambda: state.releases, get_workflow=workflow)
    def get_repo(name):
        assert name == "Code-dot-mil/SkLC"
        return remote
    monkeypatch.setattr(github, "Github", lambda **_: nullcontext(SimpleNamespace(get_repo=get_repo)))
    monkeypatch.setenv("GH_TOKEN", "test-only-placeholder")
    return SimpleNamespace(root=tmp_path, sha=sha, git=git, state=state, draft=draft, assets=assets)


def test_ready_candidate_and_matching_draft_are_approved(release_candidate):
    from types import SimpleNamespace

    from sklc_maintainer.release import check_draft, check_ready

    candidate = release_candidate
    ready = check_ready(version=VERSION, expected_commit=candidate.sha)
    assert ready["candidate_sha"] == candidate.sha
    assert ready["ci_url"] == candidate.state.run.html_url
    candidate.git("tag", f"v{VERSION}")
    candidate.state.tag = SimpleNamespace(type="commit", sha=candidate.sha)
    candidate.state.releases = [candidate.draft]
    result = check_draft(version=VERSION, expected_commit=candidate.sha)
    assert result["release_url"] == candidate.draft.html_url
    assert result["assets"] == {asset.name: asset.digest for asset in candidate.assets}


@pytest.mark.parametrize("problem", ["dirty", "wrong-head", "existing-tag", "failed-ci", "missing-ci"])
def test_readiness_rejects_unsafe_candidates(release_candidate, problem):
    from sklc_maintainer.release import check_ready

    candidate = release_candidate
    sha = candidate.sha
    if problem == "dirty":
        (candidate.root / "untracked.txt").write_text("Uncommitted work")
    elif problem == "wrong-head":
        sha = "0" * 40
    elif problem == "existing-tag":
        candidate.git("tag", f"v{VERSION}")
    elif problem == "failed-ci":
        candidate.state.run.conclusion = "failure"
    else:
        candidate.state.run = None
    with pytest.raises(ReleaseError):
        check_ready(version=VERSION, expected_commit=sha)


@pytest.mark.parametrize("problem", ["wrong-tag", "notes", "missing-asset", "incomplete-asset", "digest", "api"])
def test_draft_rejects_mismatched_or_unverifiable_release(release_candidate, monkeypatch, problem):
    from types import SimpleNamespace

    import github
    from sklc_maintainer.release import check_draft

    candidate = release_candidate
    candidate.state.tag = SimpleNamespace(type="commit", sha=candidate.sha)
    candidate.state.releases = [candidate.draft]
    if problem == "wrong-tag":
        candidate.state.tag.sha = "0" * 40
    elif problem == "notes":
        candidate.draft.body = "Different release notes"
    elif problem == "missing-asset":
        candidate.assets.pop()
    elif problem == "incomplete-asset":
        candidate.assets[0].state = "new"
    elif problem == "digest":
        candidate.assets[0].digest = None
    else:
        def unavailable(**kwargs):
            raise github.GithubException(503, {"message": "Unavailable"})
        monkeypatch.setattr(github, "Github", unavailable)
    with pytest.raises(ReleaseError):
        check_draft(version=VERSION, expected_commit=candidate.sha)
