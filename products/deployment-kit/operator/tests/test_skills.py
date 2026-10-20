from pathlib import Path

import pytest
from skill_exchange.skills import discover_skills


def test_discovers_skill_metadata():
    skills = discover_skills(Path(__file__).parent / "fixtures/skills")
    assert len(skills) == 1
    skill = skills[0]
    assert skill.metadata.skill_id == "sample-skill"
    assert skill.metadata.name == "sample-skill"
    assert skill.metadata.description == "Use for sample work."
    assert skill.metadata.raw["metadata"]["ai4sdlc.category"] == "testing"
    assert len(skill.content_hash) == 64


@pytest.mark.parametrize("name,description", [("wrong-name", "Useful"), ("sample", ""), ("sample", None)])
def test_required_metadata_is_validated_before_publication(tmp_path, name, description):
    skill = tmp_path / "skills/sample"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(f"---\nname: {name}\ndescription: {description or ''}\n---\nInstructions\n")
    with pytest.raises(ValueError):
        discover_skills(tmp_path / "skills")
