"""Content hashing shared by assessment commands and package consumers."""

import hashlib
from pathlib import Path


def skill_digest(skill: Path) -> str:
    digest = hashlib.sha256(b"skill-assessment-package-v1\0")
    files = (path for path in skill.rglob("*") if path.is_file())
    for path in sorted(files, key=lambda path: path.relative_to(skill).as_posix()):
        for value in (path.relative_to(skill).as_posix().encode("utf-8"), path.read_bytes()):
            digest.update(len(value).to_bytes(8, "big"))
            digest.update(value)
    return digest.hexdigest()
