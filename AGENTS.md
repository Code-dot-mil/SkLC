# Skill Exchange Site Agent Instructions

These instructions apply to this repository.

## Project Shape

- This repository is a static skill exchange: Python builds exchange evidence and generated data, and Astro builds the static site.
- Skill packages live under `skills/<namespace>/<skill-id>/`.
- Exchange policy lives under `.exchange/`.
- Generated exchange data lives under `.exchange/generated/` and should be produced by the local publish command or CI, not hand-authored.
- Durable generated evidence is limited to BOE bundles under `.exchange/generated/boe/`. Other generated site data is derived and should not be committed.

## Configuration Rules

- Keep environment-specific settings configurable through environment variables or GitHub Actions secrets and variables.
- Do not add organization-specific or provider-specific environment variable names. Prefer generic names such as `SKILL_EXCHANGE_LLM_*`, image registry variables, and runner tag variables.
- Do not add silent fallbacks anywhere in the codebase. Hidden substitution masks defects. If fallback behavior is truly required, make it explicit in code, document the precedence, test the intended behavior, and fail closed when no valid value is available.
- Do not commit secrets, tokens, endpoint credentials, or generated bot credentials.
- Docker image references must remain configurable. Use the existing image registry, repository, tag, and full-image override variables instead of hardcoding a network-specific registry.
- Customer-facing GitLab Pages templates under `products/deployment-kit/` must keep runner routing configurable through `PAGES_RUNNER_TAG`.

## CI And Publishing

- Keep the GitHub Actions workflows self-contained under `.github/workflows/`.
- `lint` and `test` should cover site, tooling, tests, policy, lockfile, or CI changes.
- Skill review should run only for pull requests that change `skills/**/*`.
- Scheduled publication and default-branch skill-change workflows produce official exchange evidence and commit only BOE bundles.
- Node jobs must not generate exchange data; they consume artifacts produced by Python jobs.
- Exact scan cache key matches must be reused from tracked BOE bundles. Do not depend on workflow caches as the authoritative scanner-output cache.

## Local Development

- Use `just lint`, `just test`, and `just build` for local cross-stack workflows.
- Use `uv run --extra test pytest` for Python tests.
- Use `npm --prefix site run test` for Node-based site tests.
- Use `uv run python -m skill_exchange.cli publish-local --scan-mode static-only` to generate local exchange output directly.
- Prefer `.exchange/local-generated/` for local generated site data. Do not rewrite `.exchange/generated/boe/` for local convenience.

## Boundaries

- Use `scripts/skill_exchange/ci.py` for review and publish behavior. Keep local CLI commands focused on local publication.
- Do not leave red-green scaffolding or placeholder tests in the repository. Tests must prove real behavior, not merely lock package script strings, command spelling, or implementation trivia.
- Python tests must not invoke Node or npm. Node-dependent behavior belongs in `site/tests/` and must run through `npm --prefix site run test`.
- Do not hide Python generation in npm scripts or Node builds in Python tooling. Use `just` when local developer convenience needs to orchestrate both stacks.
- Remove local generated artifacts after experiments. Do not leave ignored derived `.exchange/generated/` output, caches, or build directories around as hidden workspace state. Treat `.exchange/generated/boe/` as durable evidence and do not delete or rewrite it casually.
- Do not commit `site/dist/`, `site/.astro/`, `site/node_modules/`, `.pytest_cache/`, `.venv/`, or other local build/cache output.
- Keep documentation free of local machine paths and local workspace state.
