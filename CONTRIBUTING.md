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

## First-Time Setup

Install Python 3.12, `uv`, Node.js 22, `npm`, `just`, and [NVIDIA SkillSpector](https://github.com/NVIDIA/SkillSpector). SkillSpector can be on `PATH` or configured with `SKILLSPECTOR_BIN`.

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

## Development Loop

Use local checks for fast feedback and a real GitLab pipeline as the authoritative integration signal. Local checks can validate Python, Node, generation, and site behavior, but they do not exercise GitLab rule selection, runner tags, CI variable precedence, artifact handoff, protected publication credentials, scheduled pipelines, or GitLab Pages.

Recommended loop:

1. Make the change on a branch.
2. Run the targeted Python or site checks for the files you changed.
3. Run `just ci-local` when the change crosses stacks or affects generation, packaging, policy, or the built site.
4. Push the branch and open or update a merge request.
5. Confirm that GitLab selected the expected jobs for the changed paths and that those jobs pass.
6. For changes to publication, schedules, BOE commits, artifact handoff, runner routing, or Pages, exercise the affected default-branch or scheduled pipeline in a developer-owned fork or disposable sandbox before relying on the change in the production project.

Use only sandbox-scoped credentials for sandbox testing. Do not copy production publisher, review-comment, scanner-provider, or registry credentials into a personal test project.

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

The GitLab CI definition must remain standalone in `.gitlab-ci.yml`; do not import external CI components.

When changing CI:

- Keep runner tags configurable.
- Keep Docker image registry, repository, tag, and full-image override variables configurable.
- Keep environment-specific credentials, endpoints, scanner install commands, and bot settings in CI variables.
- Do not introduce organization-specific variable names.
- Preserve the path rules: lint, test, and audit run for site/tooling/test/policy/lockfile/CI changes; skill review runs only for `skills/**/*` changes; deploy runs from default-branch push pipelines and schedules.
- Validate with `glab ci lint` when GitLab access is available.

### Expected Pipeline Coverage

Use the job selection itself as part of CI validation:

| Pipeline and change | Jobs selected by that rule |
|---|---|
| Merge request changing site, tooling, tests, policy, lockfiles, or CI | `lint:python`, `lint:site`, `test:python`, `test:site`, `audit:python`, and `audit:site` |
| Merge request changing `skills/**/*` | `review:skills` |
| Default-branch push changing `skills/**/*` | `publish:exchange`, then `pages` |
| Default-branch push without skill changes | `generate:exchange`, then `pages` |
| Scheduled pipeline | `publish:exchange`, then `pages` |

These rows are cumulative when a change matches more than one path rule. For example, a merge request that changes both site code and a skill runs the lint, test, and audit jobs as well as `review:skills`.

A merge request pipeline does not run `publish:exchange`, `generate:exchange`, or `pages`, so a passing merge request pipeline does not prove publication or deployment behavior.

For changes that affect those jobs, use a fork or disposable sandbox with the branch under test as its default branch and representative non-production CI variables. Verify the applicable publication job and `pages` job, then inspect their artifacts:

- `review:skills` should contain only reviewer output under `review-artifacts/`.
- `publish:exchange` should contain `.exchange/generated/` and `publish-result.json`.
- `generate:exchange` should contain `.exchange/generated/` and `generate-result.json`.
- `pages` should publish a top-level `public/` artifact built from the Python job's generated data.

When testing BOE commit behavior, allow the test identity to write only to the sandbox repository. Confirm that only BOE bundles under `.exchange/generated/boe/` are durable repository changes; derived catalog data remains artifact-only.

## Generated Files

Do not hand-edit generated exchange data under `.exchange/generated/`. BOE bundles under `.exchange/generated/boe/` are durable generated evidence. Derived site data such as `index.json`, `tables/`, `skills/`, `scanner-runs/`, and `zips/` should be regenerated locally or by CI and not committed.

Do not commit local caches or build output such as `site/dist/`, `site/.astro/`, `site/node_modules/`, `.pytest_cache/`, or `.venv/`.

## Documentation

Documentation should not expose local machine paths, local workspace state, secrets, or personal tokens.

Use generic environment variable names and describe environment-specific defaults as configurable. The repository is expected to move between networks.

## Review Checklist

Keep changes focused and reviewable. A typical platform change should include:

- The implementation change.
- Tests or validation coverage for changed behavior.
- Documentation updates when operators or developers need to know about the change.
- A conventional commit message.

Before requesting review, confirm:

- Relevant targeted checks pass, and `just ci-local` passes for cross-stack or generation changes.
- `glab ci lint` passes when `.gitlab-ci.yml` changed and GitLab access is available.
- The merge request pipeline selected the jobs expected for the changed paths.
- Publication or Pages changes were exercised through a representative sandbox default-branch or scheduled pipeline.
- Generated artifacts contain only the intended exchange data, result files, reviewer output, or `public/` site content and do not expose credentials or unrelated runtime state.
- `README.md`, `CI.md`, `GOVERNANCE.md`, and `SPEC.md` were reviewed and updated when the change altered the behavior they define.

Describe both local validation and GitLab pipeline validation in the merge request. If a representative sandbox test was not applicable, say why rather than implying that local checks covered GitLab-only behavior.
