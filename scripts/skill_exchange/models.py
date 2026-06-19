from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SkillMetadata:
    namespace: str
    skill_id: str
    name: str
    description: str
    category: str | None = None
    tags: tuple[str, ...] = ()
    owner: str | None = None
    upstream_url: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def display_id(self) -> str:
        return f"{self.namespace}/{self.skill_id}"


@dataclass(frozen=True)
class SkillPackage:
    metadata: SkillMetadata
    path: Path
    skill_file: Path
    content_hash: str


@dataclass(frozen=True)
class ValidationResult:
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    metadata_flags: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.errors
