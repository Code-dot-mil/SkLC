from skill_exchange.frontmatter import parse_frontmatter


def test_parse_frontmatter_and_body():
    text = """---
name: sample-skill
description: Use for sample work.
metadata:
  ai4sdlc.category: testing
  ai4sdlc.tags: tests,example
---

# Sample Skill
"""

    frontmatter, body = parse_frontmatter(text)

    assert frontmatter["name"] == "sample-skill"
    assert frontmatter["metadata"]["ai4sdlc.category"] == "testing"
    assert frontmatter["metadata"]["ai4sdlc.tags"] == "tests,example"
    assert body.strip() == "# Sample Skill"


def test_parse_frontmatter_rejects_missing_block():
    try:
        parse_frontmatter("# No frontmatter")
    except ValueError as exc:
        assert "frontmatter" in str(exc)
    else:
        raise AssertionError("expected ValueError")
