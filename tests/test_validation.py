from dataclasses import replace
from pathlib import Path

from skill_exchange.models import SkillPackage
from skill_exchange.policy import load_exchange_policy
from skill_exchange.skills import discover_skills
from skill_exchange.validation import validate_skill


def test_validation_accepts_valid_fixture():
    policy = load_exchange_policy(Path(".exchange"))
    skill = discover_skills(Path("tests/fixtures/skills"))[0]

    result = validate_skill(skill, policy)

    assert result.errors == ()
    assert "missing_owner" not in result.metadata_flags


def test_validation_warns_for_unknown_category_and_tag():
    policy = load_exchange_policy(Path(".exchange"))
    skill = discover_skills(Path("tests/fixtures/skills"))[0]
    metadata = replace(skill.metadata, category="not-a-category", tags=("unknown-tag",))
    changed = SkillPackage(
        metadata=metadata,
        path=skill.path,
        skill_file=skill.skill_file,
        content_hash=skill.content_hash,
    )

    result = validate_skill(changed, policy)

    assert "unknown category: not-a-category" in result.warnings
    assert "unknown tag: unknown-tag" in result.warnings


def test_validation_flags_missing_owner():
    policy = load_exchange_policy(Path(".exchange"))
    skill = discover_skills(Path("tests/fixtures/skills"))[0]
    metadata = replace(skill.metadata, owner=None)
    changed = SkillPackage(
        metadata=metadata,
        path=skill.path,
        skill_file=skill.skill_file,
        content_hash=skill.content_hash,
    )

    result = validate_skill(changed, policy)

    assert "missing_owner" in result.metadata_flags
