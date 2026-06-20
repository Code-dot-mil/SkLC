# Skill Exchange Site Agent Instructions

These instructions apply to this repository.

## Project Shape

- This repository is a static skill exchange: Python builds exchange evidence and generated data, and Astro builds the static site.
- Skill packages live under `skills/<namespace>/<skill-id>/`.
- Exchange policy lives under `.exchange/`.
- Generated exchange data lives under `.exchange/generated/` and should be produced by the local publish command or CI, not hand-authored.

## Configuration Rules

- Keep environment-specific settings configurable through environment variables or GitLab CI variables.
- Do not add organization-specific or provider-specific environment variable names. Prefer generic names such as `SKILL_EXCHANGE_LLM_*`, image registry variables, and runner tag variables.
- Do not commit secrets, tokens, endpoint credentials, or generated bot credentials.
- Docker image references must remain configurable. Use the existing image registry, repository, tag, and full-image override variables instead of hardcoding a network-specific registry.
- GitLab Pages runner routing must remain configurable through `PAGES_RUNNER_TAG`.

## CI And Publishing

- The GitLab CI definition is standalone in `.gitlab-ci.yml`; do not import external CI components.
- `lint`, `test`, and `audit` should run only for site, tooling, tests, policy, lockfile, or CI changes.
- Skill review should run only for merge requests that change `skills/**/*`.
- Scheduled publication produces official exchange evidence and may commit generated output only when bot variables are configured.
- The GitLab Pages job must be named `pages` and must publish a top-level `public/` artifact.

## Local Development

- Use `npm run lint` for Python and site lint checks.
- Use `npm test` for Python tests.
- Use `npm run test:site` for Node-based site tests.
- Use `npm run build` for the Astro build.
- Use `uv run python -m skill_exchange.cli publish-local` to generate local exchange output.

## Boundaries

- Use `scripts/skill_exchange/ci.py` for review and publish behavior. Keep local CLI commands focused on local publication.
- Do not commit `site/dist/`, `site/.astro/`, `site/node_modules/`, `.pytest_cache/`, `.venv/`, or other local build/cache output.
- Keep documentation free of local machine paths and local workspace state.
