# Contributing To Skill Exchange Site

This guide is for developers changing the skill exchange application, CI, policy tooling, documentation, or static site. It is not the workflow for publishing a skill package to the exchange.

For skill governance and skill review roles, see `GOVERNANCE.md`.

## Development Scope

Exchange-site developers maintain:

- Python tooling under `scripts/skill_exchange/`.
- The Astro site under `site/`.
- GitLab CI in `.gitlab-ci.yml`.
- Exchange policy files under `.exchange/`.
- Developer and operator documentation.
- Tests for validation, generated data, CI behavior, site behavior, and security-sensitive rendering.

Skill packages under `skills/` are exchange content. Treat changes there as skill contributions, not exchange-site platform changes.

## Local Checks

Use the root package scripts for routine development:

```sh
npm run lint
npm test
npm run test:site
npm run typecheck
npm run build
```

`npm run ci:local` runs the common local gate:

```sh
npm run ci:local
```

The root scripts delegate to `uv` for Python checks and to `site/package.json` for frontend checks. They are intentionally thin wrappers so local development and CI stay aligned.

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

The site must be able to build from a fresh checkout before scheduled generated data exists. When `.exchange/generated/` data is absent, the site should render a valid empty catalog rather than failing import resolution.

## CI Changes

The GitLab CI definition must remain standalone in `.gitlab-ci.yml`; do not import external CI components.

When changing CI:

- Keep runner tags configurable.
- Keep Docker image registry, repository, tag, and full-image override variables configurable.
- Keep environment-specific credentials, endpoints, scanner install commands, and bot settings in CI variables.
- Do not introduce organization-specific variable names.
- Preserve the path rules: lint, test, and audit run for site/tooling/test/policy/lockfile/CI changes; skill review runs only for `skills/**/*` changes; deploy runs from default-branch push pipelines.
- Validate with `glab ci lint` when GitLab access is available.

## Generated Files

Do not hand-edit generated exchange data under `.exchange/generated/`. Use local publication commands or CI publication jobs to regenerate it.

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

Before pushing, run the relevant local checks. For CI or release behavior, prefer running the full `npm run ci:local` gate plus `glab ci lint` when available.
