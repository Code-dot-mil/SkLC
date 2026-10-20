# Skill Exchange Site Agent Instructions

These instructions apply to this repository.

## Development Workflow

- Before implementing or reviewing code, read [CODING_STANDARDS.md](CODING_STANDARDS.md). Use the originating task and later accepted decisions to establish scope.
- For substantial planning, roadmap decomposition, or expanding implementation scope, use [scope-maintainable-contribution](.agents/skills/scope-maintainable-contribution/SKILL.md).
- For implementing agreed code changes, use [implement](.agents/skills/implement/SKILL.md).
- When adding, revising, or reviewing tests, use [durable-behavior-tests](.agents/skills/durable-behavior-tests/SKILL.md).
- For branch, PR, or local-change reviews, use [code-review](.agents/skills/code-review/SKILL.md) with the originating task and current accepted decisions.
- When writing or editing skills or agent instructions, use [writing-for-agents](.agents/skills/writing-for-agents/SKILL.md).
- For requested pair programming or delegated coding, use [pair-programming](.agents/skills/pair-programming/SKILL.md).
- For a requested session retrospective, use [retro](.agents/skills/retro/SKILL.md).

For the next three substantive contributions, record skills used, the initial outcome, additions removed at the first checkpoint, acceptance evidence, and maintainer corrections in the existing task or PR notes. After the third contribution, assess whether the guidance reduced correction burden before adding more instructions.

## Release Requests

- When asked to check release readiness, prepare a release, create a draft, or publish, read `.agents/skills/sklc-release-process/SKILL.md` before starting release checks or a general project review. Follow its stage-specific commands instead of duplicating their checks manually.
- The release workflow prepares the draft and its assets; publication uses that existing draft. Do not create a competing release from the agent session.
- Validate release tooling through the release process itself. Do not add automated tests for the release script.

## Project Shape

- This repository is a static skill exchange: Python reads tracked evidence and builds generated data, and Astro builds the static site.
- The standalone assessment CLI lives under `products/assessment-kit/` and must not depend on site or exchange tooling.
- Define assessment commands in `skill_assessment/commands/<command>.py`. Each module owns its command name, option flags, argument parsing, and execution through `register(subparsers)` and `run(args)`; `cli.py` only registers and dispatches commands.
- Skill packages live under `skills/<namespace>/<skill-id>/`.
- Exchange policy lives under `.exchange/`.
- Generated exchange data lives under `.exchange/generated/` and should be produced by the local publish command or CI, not hand-authored.
- Durable generated evidence is limited to BOE bundles under `.exchange/generated/boe/`. Other generated site data is derived and should not be committed.

## Configuration Rules

- Keep environment-specific settings configurable through environment variables or GitHub Actions secrets and variables.
- Do not add organization-specific or provider-specific environment variable names. Prefer generic image registry variables and runner tag variables.
- Do not add silent fallbacks anywhere in the codebase. Hidden substitution masks defects. If fallback behavior is truly required, make it explicit in code, document the precedence, test the intended behavior, and fail closed when no valid value is available.
- Do not commit secrets, tokens, endpoint credentials, or generated bot credentials.
- Keep authentication material out of diagnostic output; redact request headers and credential-bearing exception details before displaying them.
- Docker image references must remain configurable. Use the existing image registry, repository, tag, and full-image override variables instead of hardcoding a network-specific registry.
- Customer-facing GitLab Pages templates under `products/deployment-kit/` must keep runner routing configurable through `PAGES_RUNNER_TAG`.

## CI And Publishing

- Keep the GitHub Actions workflows self-contained under `.github/workflows/`.
- `lint` and `test` should cover site, tooling, tests, policy, lockfile, or CI changes.
- Prebuilt site generation reads verified exact-content tracked BOE. Operator site generation reads the preceding assessment job's latest per-skill output without verifying hashes. Neither path runs assessments or writes new evidence.
- Node jobs must not generate exchange data; they consume artifacts produced by Python jobs.

## Local Development

- Use `just lint`, `just test`, and `just build` for local cross-stack workflows.
- Use `uv run --extra test pytest` for Python tests.
- Use `npm --prefix site run test` for Node-based site tests.
- Use `uv run python -m skill_exchange.cli publish-local --scan-mode static-only` to generate local exchange output directly.
- Prefer `.exchange/local-generated/` for local generated site data. Do not rewrite `.exchange/generated/boe/` for local convenience.

## Boundaries

- Do not leave red-green scaffolding or placeholder tests in the repository. Tests must prove real behavior, not merely lock package script strings, command spelling, or implementation trivia.
- Python tests must not invoke Node or npm. Node-dependent behavior belongs in `site/tests/` and must run through `npm --prefix site run test`.
- Do not hide Python generation in npm scripts or Node builds in Python tooling. Use `just` when local developer convenience needs to orchestrate both stacks.
- Remove local generated artifacts after experiments. Do not leave ignored derived `.exchange/generated/` output, caches, or build directories around as hidden workspace state. Treat `.exchange/generated/boe/` as durable evidence and do not delete or rewrite it casually.
- Do not commit `site/dist/`, `site/.astro/`, `site/node_modules/`, `.pytest_cache/`, `.venv/`, or other local build/cache output.
- Keep documentation free of local machine paths and local workspace state.
- Pass PR/MR prose through structured arguments or literal body files.
