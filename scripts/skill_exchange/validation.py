from __future__ import annotations

from .models import SkillPackage, ValidationResult
from .policy import ExchangePolicy


def validate_skill(skill: SkillPackage, policy: ExchangePolicy) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    metadata_flags: list[str] = []
    metadata = skill.metadata

    if metadata.name != metadata.skill_id:
        errors.append(f"name must match skill folder id: expected {metadata.skill_id}, got {metadata.name}")
    if not metadata.description.strip():
        errors.append("description is required")

    declared_namespace = metadata.raw.get("metadata", {}).get("ai4sdlc.namespace")
    if declared_namespace and declared_namespace != metadata.namespace:
        warnings.append(f"metadata namespace {declared_namespace} does not match folder namespace {metadata.namespace}")

    if metadata.category and metadata.category not in policy.categories:
        warnings.append(f"unknown category: {metadata.category}")

    for tag in metadata.tags:
        if tag not in policy.tags:
            warnings.append(f"unknown tag: {tag}")

    if not metadata.owner:
        metadata_flags.append("missing_owner")

    return ValidationResult(errors=tuple(errors), warnings=tuple(warnings), metadata_flags=tuple(metadata_flags))
