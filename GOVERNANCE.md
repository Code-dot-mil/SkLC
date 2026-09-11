# Skill Exchange Governance

This repository uses a lightweight governance model for the static skill exchange MVP. The repository is the source of truth for human-authored skill content and exchange policy. CI is the source of truth for generated evidence.

## Trust Boundary

Human contributors may author skill content, skill metadata, and proposed exchange policy changes. They must not author official generated evidence.

Official bill-of-evidence bundles are produced by protected scheduled CI. Candidate pull request scanner output is reviewer context only; it is not official evidence. Generated exchange index files, scanner tables, runtime zip artifacts, and public scanner-run mirrors are deploy-time projections of BOE and source skills.

## Roles

| Role | Responsibilities |
|---|---|
| Contributor | Proposes new or changed skills by pull request and responds to review feedback. |
| Skill owner | Optional in the MVP. Accountable for declared skill purpose, usefulness, and maintenance. |
| Reviewer | Reviews skill content, metadata, validation warnings, and [NVIDIA SkillSpector](https://github.com/NVIDIA/SkillSpector) assessment context. |
| Maintainer | Owns merge authority and protects governance files, CI configuration, exchange policy, and publication rules. |
| Exchange bot | Runs protected publication, produces official BOE bundles, commits BOE evidence, and publishes verified artifacts. |

The exchange bot is the only actor that may produce or commit official generated BOE.

## Human Skill Change Workflow

1. A contributor opens a pull request with a new or changed skill under `skills/`.
2. Pull request CI validates package structure and inline `SKILL.md` metadata.
3. Pull request CI warns on unknown category or tag values.
4. Pull request CI runs SkillSpector.
5. Pull request CI prepares reviewer-facing assessment artifacts and posts a comment for same-repository contributions.
6. At least one human reviewer inspects the diff, metadata, validation output, and scanner context.
7. A maintainer merges after required human approvals.
8. The protected scheduled publication pipeline produces or reuses official BOE for the default branch.
9. The exchange bot commits BOE bundles under `.exchange/generated/boe/` when bot publication is configured.
10. GitHub Actions publishes verified static-site and release artifacts.

## Generated Output Workflow

Generated output belongs under `.exchange/generated/`. BOE bundles under `.exchange/generated/boe/` are the durable generated evidence committed to the repository. They may include BOE records, exact native scanner output, scanner summaries, redacted scanner configuration, and supporting hashes.

BOE bundles are also the authoritative scan reuse source. When a later publication computes the same skill content hash, scanner version, scan mode, and scanner configuration, it should reuse the matching BOE bundle instead of re-running the scanner.

Generated index files, scanner tables, public scanner-run mirrors, generated skill records, and runtime skill zip artifacts are derived deploy artifacts. They should be generated in CI or locally and should not be committed.

Generated-output pull requests from the exchange bot may be exempt from human review only when the diff is limited to BOE bundles under `.exchange/generated/boe/`.

Bot generated-output pull requests must fail validation and must not automerge when they modify human-authored skill content, exchange policy files, CI configuration, documentation, or governance files.

## Governance Rules

- Human contributors do not author official BOE.
- Pull request SkillSpector output is advisory in the MVP.
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

Future services should ingest BOE bundles as the durable evidence source and may generate their own index/table projections from that evidence model.
