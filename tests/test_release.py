from pathlib import Path

import pytest
from skill_exchange.release import ReleaseError, extract_release_notes, validate_version

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
