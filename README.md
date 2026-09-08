# SkLC Product Source

This repository builds independently consumable SkLC products. GitHub is the maintainer source of truth and release origin. Customers consume release artifacts in GitLab; they do not need this source tree or its maintainer workflows.

The first delivery path is `deployment-kit-prebuilt-<version>.tar.gz`: one verified archive containing a ready-to-serve `public/` directory, deployment-only GitLab CI, and guided documentation. The archive is committed unchanged to a clean GitLab project, where its `pages` job verifies the files and publishes them without building the site.

## Vision

The exchange should give users a simple way to discover approved skills while giving maintainers a repeatable way to evaluate and publish them. The first implementation is a static MVP:

- Contributors add catalog skills under `products/skill-catalog/skills/<namespace>/<skill-id>/`.
- CI reviews skill changes only when skill packages change.
- Scheduled publication and default-branch skill changes build official exchange evidence and generated catalog data.
- GitLab Pages deploys the static site from generated data on default-branch pushes and scheduled publication pipelines.
- All environment-specific details, including images, scanner installation, credentials, runner tags, and deployment routing, stay configurable through environment variables or CI variables.

The long-term direction is to keep this exchange portable: a target environment should be able to supply its own registry, runner tags, credentials, scanner installation command, and publication cadence without changing repository code.

## How It Works

The current prebuilt release is assembled from three independently owned source areas:

1. Catalog packages live under `products/skill-catalog/skills/`. Each package contains a `SKILL.md` file with frontmatter and skill content.
2. Maintainer tooling under `maintainer/skill_exchange/` validates source inputs, applies maintainer policy, writes BOE and derived site data under `maintainer/exchange/generated/`, and assembles release artifacts.
3. Deployment-kit site source under `products/deployment-kit/site/` consumes generated data. Prebuilt deployment files under `products/deployment-kit/prebuilt/` are added only when the release package is assembled.

Tracked generated evidence lives under `maintainer/exchange/generated/boe/`. Other generated outputs under `maintainer/exchange/generated/` are deploy-time site inputs and should not be committed.

BOE bundles are also the durable scanner cache. If a later publication computes the same skill identity, content hash, SkillSpector version, scan mode, and scanner configuration, the builder reuses the matching BOE bundle and regenerates derived site data without running the scanner again.

## Repository Map

- `products/skill-catalog/` owns the catalog release policy, README, and source skill packages.
- `products/deployment-kit/site/` owns the Astro reference-site source and pinned Node tooling.
- `products/deployment-kit/prebuilt/` owns the deployment-only GitLab CI and customer documentation placed in the prebuilt release.
- `maintainer/exchange/` stores maintainer policy, display configuration, tags, categories, BOE, and generated catalog output.
- `maintainer/skill_exchange/` contains Python maintainer tooling and release assembly.
- `.gitlab-ci.yml` defines the standalone GitLab CI pipeline.
- `CI.md` documents CI variables, schedules, review behavior, and deploy behavior.
- `CONTRIBUTING.md` explains how developers contribute to the exchange application, tooling, CI, and documentation.
- `contracts/` contains draft versioned schemas and examples for serialized interfaces shared across the planned product boundaries; current runtime output remains on the implemented `v0` formats.
- `docs/architecture.md` documents the current component, evidence, catalog-build, and CI flows.
- `docs/roadmap.md` defines the Q3 2026 target product, GitHub release, and downstream delivery plan.
- `GOVERNANCE.md` describes exchange roles, review flow, generated-output boundaries, and bot publication rules.
- `tests/` contains Python tests for exchange tooling and CI behavior.

## Developer Setup

Install the local toolchain:

- Python 3.12 with `uv`.
- Node.js 22 with `npm`.
- `just` for cross-stack commands.
- SkillSpector on `PATH`, or `SKILLSPECTOR_BIN` pointing to a SkillSpector binary, when running local generation or deploy-equivalent builds.

Install dependencies:

```sh
uv sync --extra test
npm ci --prefix products/deployment-kit/site
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

Local `just` generation writes to `maintainer/exchange/local-generated/` so developers do not accidentally rewrite tracked CI-produced BOE. Use `uv` directly for Python-only checks and `npm --prefix products/deployment-kit/site` for site-only checks. `just` is the local developer wrapper when a task intentionally spans both stacks.

Use [CONTRIBUTING.md](CONTRIBUTING.md) for exchange-site development workflow details.

## CI Workflow

The GitLab pipeline has six stages: `lint`, `test`, `audit`, `review`, `publish`, and `deploy`.

- `lint`, `test`, and `audit` run only when site code, exchange tooling, tests, lockfiles, policy, or CI configuration changes.
- `review:skills` runs only for merge requests that change `products/skill-catalog/skills/**/*`.
- `publish:exchange` runs from scheduled pipelines and default-branch skill-change pipelines, and can commit BOE bundles when bot variables are configured.
- `generate:exchange` runs on default-branch push pipelines that do not change skills, and produces deploy-time generated site artifacts.
- `pages` runs on default-branch push pipelines and scheduled publication pipelines, consuming generated artifacts and publishing a top-level `public/` artifact for GitLab Pages.
- GitHub Dependabot owns dependency-vulnerability alerts and remediation pull requests.

See [CI.md](CI.md) for the full configuration reference.

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

The prebuilt package is static and ready to serve. It does not contain site source, build tools, assessment tooling, a live application server, an interactive approval workflow, or operator-managed update behavior. Those belong to separate products or later milestones in [the roadmap](docs/roadmap.md).
