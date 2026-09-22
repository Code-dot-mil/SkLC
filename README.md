# Skill Exchange Site

Skill Exchange Site is a static catalog for publishing agent skills with review evidence, risk signals, and downloadable runtime bundles. The goal is to make skill sharing boring and inspectable: every listed skill should have clear metadata, policy validation, scanner output, and a generated bill of evidence before it is promoted through the exchange.

This repository is intentionally self-contained. The site, exchange builder, CI helpers, policy files, and GitHub Actions workflows all live here. Customer-facing GitLab deployment templates are packaged separately under `products/deployment-kit/`.

## Use the prebuilt site

The prebuilt deployment kit contains an already-built site. Customers need an
archive extractor and Python 3.12 or newer for offline verification, but no Node.js,
`uv`, site build, or assessment tools.

Choose the download:

- **Published release:** When a prebuilt version is available in
  [GitHub Releases](https://github.com/Code-dot-mil/SkLC/releases), download
  `deployment-kit-prebuilt-<version>.tar.gz`, not the automatically generated
  source-code archives. Follow the
  [installation guide](products/deployment-kit/docs/prebuilt/install.md) to extract
  it and verify the selected version.
- **CI test build:** From a successful
  [CI run](https://github.com/Code-dot-mil/SkLC/actions/workflows/ci.yml) that includes
  prebuilt packaging, download the `static-site` artifact ZIP. This is not a
  published product release. Extract the ZIP to get the complete package (no tar
  archive to unpack), then run the verification command below.
  See [CI package details](CI.md#github-validation).

From the extracted package root (the folder containing `public/`, `README.md`,
and `.gitlab-ci.yml`, not this source repository), run the shared verifier:

```sh
python3 -I -S scripts/verify_prebuilt.py .
```

Stop if verification fails. Once it passes, follow the included README or choose:

- [GitLab Pages](products/deployment-kit/docs/prebuilt/deploy-gitlab-pages.md): copy
  the complete package, including hidden files. Configure `PAGES_RUNNER_TAG` for
  an available Linux runner that supports and can pull the job's Python image.
- [Another static host](products/deployment-kit/docs/prebuilt/deploy-static-hosting.md):
  serve the complete `public/` directory unchanged, at a domain root or URL prefix.

The developer setup below is for working on the source, not deploying this package.

## Download the four skills

Download `skill-catalog-<version>.tar.gz` and its matching `.tar.gz.sha256` file
from [GitHub Releases](https://github.com/Code-dot-mil/SkLC/releases), when published.
The archive contains the four developer skill folders, their supporting files,
and a [short installation README](products/skill-catalog/README.md). Extract it
and copy the folders into your workspace's `.agents/skills/`.
For PR testing, the `skill-catalog` CI artifact contains the same layout.

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
- Official publication uses upstream SkillSpector 2.10.0 with its native OpenAI-compatible provider and commits only durable BOE bundles.
- GitHub Dependabot owns dependency-vulnerability alerts and remediation pull requests.

See [CI.md](CI.md) for the full configuration reference.

## Configuration

Configuration is part of the portability model. Do not hardcode network-specific values into the repository. Use CI variables or environment variables for:

- Python and Node image registry, repository, tag, or full image override.
- Customer GitLab runner tags for packaged Pages deployment.
- SkillSpector binary path or the locked `scan` dependency extra.
- LLM-assisted scan provider endpoint, model, and API key.
- Pull request comment behavior.
- Scheduled publication branch, bot identity, push URL, and token.
- Audit thresholds and scan modes.

Secrets should be configured as masked CI variables in the target environment and must not be committed.

## Current Boundaries

This is a static exchange MVP. It does not implement a live application server, interactive approval workflow, protected-branch administration, hosting-provider API simulation, or user account model. Those responsibilities belong to the hosting platform and future exchange services.
