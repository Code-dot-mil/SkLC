# Skill Exchange Governance

This repository uses a lightweight governance model for the static skill exchange MVP. The repository is the source of truth for human-authored skill content and exchange policy. CI is the source of truth for generated evidence.

## Trust Boundary

Human contributors may author skill content, skill metadata, and proposed exchange policy changes. They must not author official generated evidence.

Official bill-of-evidence records, generated exchange index files, scanner tables, and runtime zip artifacts are produced by protected scheduled CI. Candidate MR scanner output is reviewer context only; it is not official evidence.

## Roles

| Role | Responsibilities |
|---|---|
| Contributor | Proposes new or changed skills by merge request and responds to review feedback. |
| Skill owner | Optional in the MVP. Accountable for declared skill purpose, usefulness, and maintenance. |
| Reviewer | Reviews skill content, metadata, validation warnings, and SkillSpector assessment context. |
| Maintainer | Owns merge authority and protects governance files, CI configuration, exchange policy, and publication rules. |
| Exchange bot | Runs protected scheduled publication, produces official BOE, commits generated exchange data, and publishes Pages output. |

The exchange bot is the only actor that may produce or commit official generated BOE.

## Human Skill Change Workflow

1. A contributor opens a merge request with a new or changed skill under `skills/`.
2. MR CI validates package structure and inline `SKILL.md` metadata.
3. MR CI warns on unknown category or tag values.
4. MR CI runs SkillSpector when feasible.
5. MR CI prepares reviewer-facing assessment artifacts and may post a merge request comment when comment credentials are configured.
6. At least one human reviewer inspects the diff, metadata, validation output, and scanner context.
7. A maintainer merges after required human approvals.
8. The protected scheduled publication pipeline produces or reuses official BOE for the default branch.
9. The exchange bot commits generated exchange data under `.exchange/generated/` when bot publication is configured.
10. GitLab Pages publishes the updated static exchange.

## Generated Output Workflow

Generated output belongs under `.exchange/generated/`. It may include BOE records, scanner reports, scanner summary tables, generated skill records, and runtime skill zip artifacts.

Generated-output merge requests from the exchange bot may be exempt from human review only when the diff is limited to generated evidence, generated index files, scanner tables, and generated zip artifacts under `.exchange/generated/`.

Bot generated-output merge requests must fail validation and must not automerge when they modify human-authored skill content, exchange policy files, CI configuration, documentation, or governance files.

## Governance Rules

- Human contributors do not author official BOE.
- MR SkillSpector output is advisory in the MVP.
- Official BOE comes from protected scheduled CI.
- Unknown categories and tags warn in CI, but do not fail publication in the MVP.
- Maintainers may reject unhelpful category or tag values during human review.
- New or changed skills require at least one human reviewer before merge.
- Risk levels are displayed for every visible skill.
- Skills with `Unknown` risk are shown or hidden according to `.exchange/display-policy.yaml`.
- LLM-assisted and static-only scans must be distinguishable through scan mode and confidence flags.
- Exchange policy, CI behavior, runner routing, image selection, scanner installation, and provider credentials must remain configurable for the target environment.

## Current MVP Boundaries

The MVP does not include a backend approval service, user account model, custom AI review workflow, executable evaluation harness, download tracking, or formal blocking gate based on SkillSpector findings. Those may be added later only after the static exchange data contract and governance boundary prove useful.

Future services should ingest `.exchange/generated/index.json` and BOE records rather than replacing the bot-produced evidence model.
