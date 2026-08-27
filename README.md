# Skill Exchange Site

Skill Exchange Site is a static catalog for publishing agent skills with review evidence, risk signals, and downloadable runtime bundles. The goal is to make skill sharing boring and inspectable: every listed skill should have clear metadata, policy validation, scanner output, and a generated bill of evidence before it is promoted through the exchange.

This repository is intentionally self-contained. The site, exchange builder, CI helpers, policy files, GitHub Actions workflows, and legacy GitLab CI definition all live here so the project can move between networks without importing environment-specific CI components.

## Vision

The exchange should give users a simple way to discover approved skills while giving maintainers a repeatable way to evaluate and publish them. The first implementation is a static MVP:

- Contributors add skills under `skills/<namespace>/<skill-id>/`.
- CI reviews skill changes only when skill packages change.
- Scheduled publication and default-branch skill changes build official exchange evidence and generated catalog data.
- GitHub Actions validates and packages the static site, reviews changed skills, and publishes official evidence from default-branch skill changes and scheduled publication runs.
- All environment-specific details, including images, scanner installation, credentials, runner tags, and deployment routing, stay configurable through environment variables or CI variables.

The long-term direction is to keep this exchange portable: a target environment should be able to supply its own registry, runner tags, credentials, scanner installation command, and publication cadence without changing repository code.

## How It Works

The exchange has three main layers:

1. Skill packages live under `skills/`. Each package contains a `SKILL.md` file with frontmatter and skill content.
2. Python tooling under `scripts/skill_exchange/` validates skills, runs [NVIDIA SkillSpector](https://github.com/NVIDIA/SkillSpector), applies exchange policy, writes bill-of-evidence bundles, creates runtime zip files, and produces derived site data under `.exchange/generated/`.
3. The Astro site under `site/` reads derived `.exchange/generated/` data and builds a static catalog artifact.

Tracked generated evidence lives under `.exchange/generated/boe/`. Other generated outputs under `.exchange/generated/` are deploy-time site inputs and should not be committed.

BOE bundles are also the durable scanner cache. If a later publication computes the same skill identity, content hash, SkillSpector version, scan mode, and scanner configuration, the builder reuses the matching BOE bundle and regenerates derived site data without running the scanner again.

## Repository Map

- `.exchange/` stores exchange policy, display configuration, tags, categories, and generated catalog output.
- `.github/workflows/ci.yml` validates the codebase and builds preview catalog artifacts.
- `.github/workflows/skillspector.yml` reviews changed skills and publishes official SkillSpector evidence.
- `.gitlab-ci.yml` preserves the standalone legacy GitLab CI pipeline.
- `CI.md` documents CI variables, schedules, review behavior, and deploy behavior.
- `CONTRIBUTING.md` explains how developers contribute to the exchange application, tooling, CI, and documentation.
- `contracts/` contains draft versioned schemas and examples for serialized interfaces shared across the planned product boundaries; current runtime output remains on the implemented `v0` formats.
- `docs/architecture.md` documents the current component, evidence, catalog-build, and CI flows.
- `docs/roadmap.md` defines the Q3 2026 target product, GitHub release, and downstream delivery plan.
- `GOVERNANCE.md` describes exchange roles, review flow, generated-output boundaries, and bot publication rules.
- `scripts/skill_exchange/` contains Python exchange tooling and CI entry points.
- `site/` contains the Astro static site.
- `skills/` contains skill packages included in the exchange.
- `tests/` contains Python tests for exchange tooling and CI behavior.

## Developer Setup

Install the local toolchain:

- Python 3.12 with `uv`.
- Node.js 22 with `npm`.
- `just` for cross-stack commands.
- The locked `scan` dependency extra, SkillSpector on `PATH`, or `SKILLSPECTOR_BIN` pointing to a SkillSpector binary when running local generation or deploy-equivalent builds.

Install dependencies:

```sh
uv sync --extra test
uv sync --extra scan
npm ci --prefix site
```

SkillSpector is not required for Python lint, Python tests, site lint, or site tests. It is required for `just generate`, `just build`, and CI publication jobs. Matching BOE evidence avoids scan execution, but the publication environment still needs a configured SkillSpector binary so the cache key can be computed consistently.

## Local Workflow

Run the common local checks:

```sh
just ci-local
```

Generate local exchange evidence and catalog data:

```sh
just generate
```

Build the static site from freshly generated local data:

```sh
just build
```

Pass a scan mode when needed:

```sh
just generate llm-assisted
just build llm-assisted
```

LLM-assisted scans require the generic `SKILL_EXCHANGE_LLM_*` environment variables described in [CI.md](CI.md).

Local `just` generation writes to `.exchange/local-generated/` so developers do not accidentally rewrite tracked CI-produced BOE. Use `uv` directly for Python-only checks and `npm --prefix site` for site-only checks. `just` is the local developer wrapper when a task intentionally spans both stacks.

Use [CONTRIBUTING.md](CONTRIBUTING.md) for exchange-site development workflow details.

## CI Workflow

- `CI` runs lint and tests, generates static-only preview evidence when tracked BOE is absent, builds the site, and uploads catalog artifacts.
- `SkillSpector` reviews skill pull requests and runs protected `static-only,llm-assisted` publication on default-branch skill changes, nightly schedules, and manual dispatches.
- Official publication uses upstream SkillSpector 2.10.0 with native Azure OpenAI support and commits only durable BOE bundles.
- The legacy GitLab pipeline remains tracked for migration history but is not the active GitHub control.
- GitHub Dependabot owns dependency-vulnerability alerts and remediation pull requests.

See [CI.md](CI.md) for the full configuration reference.

## Configuration

Configuration is part of the portability model. Do not hardcode network-specific values into the repository. Use CI variables or environment variables for:

- Python and Node image registry, repository, tag, or full image override.
- GitLab runner tags for CI jobs and Pages deployment.
- SkillSpector binary path or the locked `scan` dependency extra.
- LLM-assisted scan provider endpoint, model, and API key.
- Merge request comment token behavior.
- Scheduled publication branch, bot identity, push URL, and token.
- Audit thresholds and scan modes.

Secrets should be configured as masked CI variables in the target environment and must not be committed.

## Current Boundaries

This is a static exchange MVP. It does not implement a live application server, interactive approval workflow, protected-branch administration, hosting-provider API simulation, or user account model. Those responsibilities belong to the hosting platform and future exchange services.
