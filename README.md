# Skill Exchange Site

Skill Exchange Site is a static catalog for publishing agent skills with review evidence, risk signals, and downloadable runtime bundles. The goal is to make skill sharing boring and inspectable: every listed skill should have clear metadata, policy validation, scanner output, and a generated bill of evidence before it is promoted through the exchange.

This repository is intentionally self-contained. The site, exchange builder, CI helpers, policy files, and GitLab CI definition all live here so the project can move between networks without importing environment-specific CI components.

## Vision

The exchange should give users a simple way to discover approved skills while giving maintainers a repeatable way to evaluate and publish them. The first implementation is a static MVP:

- Contributors add skills under `skills/<namespace>/<skill-id>/`.
- CI reviews skill changes only when skill packages change.
- Scheduled publication builds official exchange evidence and generated catalog data.
- GitLab Pages deploys the static site from generated data on the default branch.
- All environment-specific details, including images, scanner installation, credentials, runner tags, and deployment routing, stay configurable through environment variables or CI variables.

The long-term direction is to keep this exchange portable: a target environment should be able to supply its own registry, runner tags, credentials, scanner installation command, and publication cadence without changing repository code.

## How It Works

The exchange has three main layers:

1. Skill packages live under `skills/`. Each package contains a `SKILL.md` file with frontmatter and skill content.
2. Python tooling under `scripts/skill_exchange/` validates skills, runs SkillSpector, applies exchange policy, writes bill-of-evidence records, creates runtime zip files, and produces `.exchange/generated/index.json`.
3. The Astro site under `site/` reads `.exchange/generated/index.json` and builds a static catalog that can be published by GitLab Pages.

Generated exchange data is written under `.exchange/generated/`. That directory is the contract between the publication tooling and the static site.

## Repository Map

- `.exchange/` stores exchange policy, display configuration, tags, categories, and generated catalog output.
- `.gitlab-ci.yml` defines the standalone GitLab CI pipeline.
- `CONTRIBUTING.md` explains how developers contribute to the exchange application, tooling, CI, and documentation.
- `GOVERNANCE.md` describes exchange roles, review flow, generated-output boundaries, and bot publication rules.
- `docs/ci.md` documents CI variables, schedules, review behavior, and deploy behavior.
- `docs/local-mvp.md` documents local publication commands.
- `scripts/skill_exchange/` contains Python exchange tooling and CI entry points.
- `site/` contains the Astro static site.
- `skills/` contains skill packages included in the exchange.
- `tests/` contains Python tests for exchange tooling and CI behavior.

## Local Workflow

Run the common local checks:

```sh
npm run ci:local
```

Generate local exchange evidence and catalog data:

```sh
uv run python -m skill_exchange.cli publish-local
```

Build the static site:

```sh
npm run build
```

Use [CONTRIBUTING.md](CONTRIBUTING.md) for exchange-site development workflow details. See [docs/local-mvp.md](docs/local-mvp.md) for local scan-mode details and generated output descriptions.

## CI Workflow

The GitLab pipeline has six stages: `lint`, `test`, `audit`, `review`, `publish`, and `deploy`.

- `lint`, `test`, and `audit` run only when site code, exchange tooling, tests, lockfiles, policy, or CI configuration changes.
- `review:skills` runs only for merge requests that change `skills/**/*`.
- `publish:exchange` runs only from scheduled pipelines and can commit generated exchange evidence when bot variables are configured.
- `pages` runs on default-branch push pipelines and publishes a top-level `public/` artifact for GitLab Pages.

See [docs/ci.md](docs/ci.md) for the full configuration reference.

## Configuration

Configuration is part of the portability model. Do not hardcode network-specific values into the repository. Use CI variables or environment variables for:

- Python and Node image registry, repository, tag, or full image override.
- GitLab runner tags for CI jobs and Pages deployment.
- SkillSpector binary path or installation command.
- LLM-assisted scan provider endpoint, model, and API key.
- Merge request comment token behavior.
- Scheduled publication branch, bot identity, push URL, and token.
- Audit thresholds and scan modes.

Secrets should be configured as masked CI variables in the target environment and must not be committed.

## Current Boundaries

This is a static exchange MVP. It does not implement a live application server, interactive approval workflow, protected-branch administration, GitLab API simulation, or user account model. Those responsibilities belong to the hosting GitLab environment and future exchange services.
