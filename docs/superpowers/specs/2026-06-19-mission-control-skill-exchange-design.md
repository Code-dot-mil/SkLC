# Mission Control Skill Exchange Design

Date: 2026-06-19

## Goal

Make the static skill exchange feel like a simple, high-trust mission operations tool while fixing the highest-value non-CI review findings.

## Scope

This pass keeps the local static exchange architecture. Real GitLab CI, protected bot publication, and GitLab Pages deployment policy are deferred. The site must not invent skill-specific usage content that is not present in the skill package. `SKILL.md` remains the primary source for what a skill does.

## Visual Direction

Use the Mission Control direction: deep near-black background, cyan signal accents, subtle network-line texture, glassy panels, crisp white text, and strong action hierarchy. The site should feel polished and operational, not decorative or marketing-heavy.

## User Language

The primary user-facing decision label remains recommendation-oriented because the target user needs simple guidance:

- `Safe to use`
- `Use caution`
- `Avoid installing`
- `Unknown`

Scanner risk remains available as supporting evidence. Risk values should not be the only or primary user label.

## UX Structure

The catalog should help users compare skills quickly using skill name, description, recommendation, category/tags, and assessment context. The detail page should lead with the skill identity, recommendation, trust snapshot, and a clear `Download skill package` action. The former `Files` tab becomes `Skill Instructions`, with `SKILL.md` shown first because it is the closest available source for what the skill does.

## Data And Safety

Generated skill records should include both recommendation fields and spec-aligned risk fields. Scanner failures should produce an `Unknown` record rather than aborting the whole publication. Validation errors should block publication outputs for invalid skills. Artifact copying and zip packaging should reject path traversal, symlinks, and unreasonable package size/count. Markdown rendering should avoid unsafe raw HTML execution while preserving useful Markdown readability.

## Testing

Add focused tests only:

- generated index contract includes recommendation, risk, risk reason, and provenance;
- scanner failure becomes `Unknown`;
- validation errors block publication;
- artifact copy rejects unsafe paths;
- zip packaging rejects symlinks and has a predictable manifest;
- skill Markdown raw HTML is not executable in rendered detail output.

