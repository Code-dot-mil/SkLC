from pathlib import Path

from skill_exchange.skills import discover_skills


def test_discover_namespaced_skill_fixture():
    root = Path("tests/fixtures")
    skills = discover_skills(root / "skills")

    assert len(skills) == 1
    skill = skills[0]
    assert skill.metadata.namespace == "ai4sdlc"
    assert skill.metadata.skill_id == "sample-skill"
    assert skill.metadata.display_id == "ai4sdlc/sample-skill"
    assert skill.metadata.category == "testing"
    assert skill.metadata.tags == ("tests", "example")
    assert skill.metadata.owner == "sample-owner"
    assert skill.metadata.upstream_url == "https://example.org/sample-skill"
    assert len(skill.content_hash) == 64
