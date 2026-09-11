# Contributing To Skill Exchange Site

This guide is for developers changing the skill exchange application, CI, policy tooling, documentation, or static site. It is not the workflow for publishing a skill package to the exchange.

For skill governance and skill review roles, see `GOVERNANCE.md`.

## Development Scope

Exchange-site developers maintain:

- Python tooling under `scripts/skill_exchange/`.
- The Astro site under `site/`.
- GitHub Actions workflows under `.github/workflows/`.
- Exchange policy files under `.exchange/`.
- Developer and operator documentation.
- Tests for validation, generated data, CI behavior, site behavior, and security-sensitive rendering.

Skill packages under `skills/` are exchange content. Treat changes there as skill contributions, not exchange-site platform changes.

## First-Time Setup

Install Python 3.12, `uv`, Node.js 22, `npm`, and `just`. Install the repository's pinned [NVIDIA SkillSpector](https://github.com/NVIDIA/SkillSpector) dependency with `uv sync --extra scan`; an independently installed binary can instead be placed on `PATH` or configured with `SKILLSPECTOR_BIN`.

Install project dependencies:

```sh
uv sync --extra test
npm ci --prefix site
```

Python-only and Node-only checks do not require SkillSpector. Generation and deploy-equivalent local builds do, because they compute scanner cache keys and produce scanner-backed exchange data before the site build.

## Local Checks

Use `just` for routine cross-stack development:

```sh
just lint
just test
just build
```

`just ci-local` runs the common local gate:

```sh
just ci-local
```

Use `uv` directly for Python-only commands and `npm --prefix site` for site-only commands. Do not hide Python work inside npm scripts or Node work inside Python tests.

`just generate` writes to `.exchange/local-generated/`, not `.exchange/generated/`, so local builds do not rewrite tracked CI-produced BOE bundles.

The default scan mode is `static-only`. Use `just generate llm-assisted` or `just build llm-assisted` only after setting the generic `SKILL_EXCHANGE_LLM_*` environment variables.

## Python Tooling

Python code must pass:

```sh
uv run --extra test ruff check scripts tests
uv run --extra test pytest
uv run python -m compileall scripts tests
```

Keep Python code focused on exchange validation, scanner orchestration, BOE generation, generated index creation, CI helpers, and packaging. Do not put frontend build behavior in Python unless it is part of generated exchange data.

## Site Tooling

Site code must pass:

```sh
npm --prefix site run lint
npm --prefix site run test
npm --prefix site run build
```

Node-based tests belong under `site/tests/`. Python pytest should not depend on Node, npm install state, or `site/node_modules`.

The site must be able to build from deploy-time generated artifacts. When `.exchange/generated/` data is absent, the site should render a valid empty catalog rather than failing import resolution.

## CI Changes

The repository's GitHub Actions workflows must remain self-contained under `.github/workflows/`. Customer-facing GitLab deployment templates under `products/deployment-kit/` are release inputs, not maintainer CI.

When changing CI:

- Keep self-hosted runner settings configurable.
- Keep customer deployment image registry, repository, tag, and full-image override variables configurable.
- Keep environment-specific credentials, endpoints, scanner install commands, and bot settings in CI variables.
- Do not introduce organization-specific variable names.
- Preserve the path rules: validation covers site/tooling/test/policy/lockfile/CI changes; skill review runs only for `skills/**/*` changes; official publication runs for default-branch skill changes and schedules.
- Keep dependency-vulnerability triage in GitHub Security; do not add a scheduled CI job that duplicates the Dependabot backlog.
- Validate changed workflow YAML and run the relevant local checks before pushing.

## Generated Files

Do not hand-edit generated exchange data under `.exchange/generated/`. BOE bundles under `.exchange/generated/boe/` are durable generated evidence. Derived site data such as `index.json`, `tables/`, `skills/`, `scanner-runs/`, and `zips/` should be regenerated locally or by CI and not committed.

Do not commit local caches or build output such as `site/dist/`, `site/.astro/`, `site/node_modules/`, `.pytest_cache/`, or `.venv/`.

## Documentation

Documentation should not expose local machine paths, local workspace state, secrets, or personal tokens.

Use generic environment variable names and describe environment-specific defaults as configurable. The repository is expected to move between networks.

## Merge Expectations

Keep changes focused and reviewable. A typical platform change should include:

- The implementation change.
- Tests or validation coverage for changed behavior.
- Documentation updates when operators or developers need to know about the change.
- A conventional commit message.

Before pushing, run the relevant local checks. For CI or release behavior, prefer running the full `just ci-local` gate.
