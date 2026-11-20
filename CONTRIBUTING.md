# Contributing To Skill Exchange Site

This guide is for developers changing the skill exchange application, CI, deployment tooling, documentation, or static site. It is not the workflow for publishing a skill package to the exchange.

For skill governance and skill review roles, see `GOVERNANCE.md`.

For product ownership, source layout, composition, CI, and test boundaries, apply the normative [product-boundary contract](docs/product-boundaries.md) when planning, implementing, and reviewing contributions.

## Development Scope

Exchange-site developers maintain:

- Python runtime under `products/deployment-kit/operator/src/skill_exchange/` and upstream tooling under `maintainer/`.
- The Astro site under `products/deployment-kit/operator/site/`.
- GitHub Actions workflows under `.github/workflows/`.
- Product-owned configuration and customer CI.
- Developer and operator documentation.
- Tests for validation, generated data, CI behavior, site behavior, and security-sensitive rendering.

Skill packages under `products/skill-bundle/` are exchange content. Treat changes there as skill contributions, not exchange-site platform changes.

For skill changes, follow [PR assessment review](CI.md#pull-request-assessment-review). Trusted same-repository PRs receive assessment; fork PRs receive no provider-backed assessment and need a maintainer to arrange matching evidence before their changed skills can build. Local generation also requires current evidence. Keep report pairs with their exact skill content; do not hand-edit evidence to make generation pass.

## First-Time Setup

Install [Python 3.12](https://www.python.org/downloads/), [uv](https://docs.astral.sh/uv/getting-started/installation/), [Node.js 22 with npm](https://nodejs.org/en/download) (22.23.4 or a newer Node 22 patch), and [just](https://just.systems/man/en/packages.html). The [local lint guide](docs/linting.md) also covers the required `actionlint` and `shellcheck` tools.

Install project dependencies:

```sh
uv sync --extra test --group lint
npm ci
npm ci --prefix products/deployment-kit/operator/site
```

Site generation reads current adjudicated assessments. No scanner installation or credentials are required.

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

Use `uv` directly for Python-only commands and `npm --prefix products/deployment-kit/operator/site` for site-only commands. Do not hide Python work inside npm scripts or Node work inside Python tests.

`just generate` writes to `products/deployment-kit/operator/.exchange/generated/`, beside the Operator site. Generation reads current assessment reports without modifying them.

Generation reads `products/skill-bundle-assessments/<skill-name>/`. Use `--evidence` with `python -m skill_exchange.cli generate` for a separate current-report root. Missing, stale, or mismatched report pairs fail generation; nonfatal partial coverage remains visible. Generation produces no evidence.

## Python Tooling

Python code must pass:

```sh
just python-lint
uv run --extra test pytest
```

Keep Python code focused on exchange validation, evidence verification, generated index creation, and packaging. Do not put frontend build behavior in Python unless it is part of generated exchange data.

## Site Tooling

Site code must pass:

```sh
npm --prefix products/deployment-kit/operator/site run lint
npm --prefix products/deployment-kit/operator/site run lint:code
npm --prefix products/deployment-kit/operator/site run typecheck:astro
npm --prefix products/deployment-kit/operator/site run test
npm --prefix products/deployment-kit/operator/site run build
```

Node-based tests belong under `products/deployment-kit/operator/site/tests/`. Python pytest should not depend on Node, npm install state, or `products/deployment-kit/operator/site/node_modules`.

Site builds and development servers always read `.exchange/generated/` beside the `site/` directory. Run `just generate` first. Lint and test commands do not require generated data. Missing data fails the build; an index containing an empty skills array renders an empty catalog.

## CI Changes

The repository's GitHub Actions workflows must remain self-contained under `.github/workflows/`. Customer-facing GitLab deployment templates under `products/deployment-kit/` are release inputs, not maintainer CI.

When changing CI:

- Keep self-hosted runner settings configurable.
- Keep customer deployment image registry, repository, tag, and full-image override variables configurable.
- Keep environment-specific deployment settings in CI variables.
- Do not introduce organization-specific variable names.
- Keep Python and site checks on pull requests and pushes to `main`. Catalog and site builds must not run assessments.
- Keep dependency-vulnerability triage in GitHub Security; do not add a scheduled CI job that duplicates the Dependabot backlog.
- Validate changed workflow YAML and run the relevant local checks before pushing.

## Generated Files

Do not hand-edit generated exchange data under `products/deployment-kit/operator/.exchange/generated/`. Current reports under `products/skill-bundle-assessments/` are durable generated evidence. Derived site data such as `index.json`, `assessments/`, and `zips/` should be regenerated locally or by CI and not committed.

Do not commit local caches or build output such as `products/deployment-kit/operator/site/dist/`, `products/deployment-kit/operator/site/.astro/`, `products/deployment-kit/operator/site/node_modules/`, `.pytest_cache/`, or `.venv/`.

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

### AI-assisted commits

For AI-assisted changes, briefly describe AI's contribution in the commit body and add the following trailers (metadata lines at the end of the message). This keeps the record with the change in Git history. For example:

```text
fix: preserve catalog filters when navigating back

AI helped draft the implementation and tests.

Assisted-by: Codex:unknown
Skills-used: code-review, durable-behavior-tests
```

- `Assisted-by` records the coding tool and model label. Repeat it for each known contributing tool/model pair, including delegated work. Use session metadata, observed tool output, or information confirmed by the developer. Use `unknown` when the model is unavailable; identify configuration-only selections explicitly, for example `Cursor:unknown (selected: Auto)`.
- `Skills-used` lists skills actually used for this contribution. Availability or installation alone does not establish use. Use `none` when no skills were used, or `unknown` when use cannot be established; retain known names alongside `unknown` when the record is incomplete. Tool versions and skill revisions are optional when readily known.

The person finalizing the commit checks the attribution. When amending or squashing, carry all known contributions into the final message and check that the trailers remain. These entries are contributor-reported attribution, not proof of exact backend model identity or compliance with skill instructions.

If your coding tool does not load `AGENTS.md`, give it this section when requesting a commit message, or add the note yourself. The same convention applies when committing work copied from a browser chat.

The `Assisted-by` format follows [OpenSSL's contribution guidance](https://github.com/openssl/openssl/blob/5be87c4438d91d7f6f28265b1d79ad9565731da3/CONTRIBUTING.md#L145). The `Skills-used` trailer is a SkLC convention adapting [PostHog's PR disclosure of agents, models, and invoked skills](https://github.com/PostHog/posthog/blob/574679ee6bff2aa7a286e272b5b418fe49ebc5cd/.github/pull_request_template.md).
