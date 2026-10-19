# Skill Exchange Site

Skill Exchange Site is a static catalog for publishing agent skills with review evidence, risk signals, and downloadable runtime bundles. The goal is to make skill sharing boring and inspectable: every listed skill should have clear metadata, policy validation, scanner output, and a generated bill of evidence before it is promoted through the exchange.

This repository is intentionally self-contained. The site, exchange builder, policy files, and GitHub Actions workflows all live here. Customer-facing GitLab deployment templates are packaged separately under `products/deployment-kit/`.

## Use the prebuilt site

The prebuilt deployment kit contains an already-built site. Download
`deployment-kit-prebuilt-<version>.zip` from
[GitHub Releases](https://github.com/Code-dot-mil/SkLC/releases), compare its SHA-256
with the digest GitHub displays for that asset, then unzip it once. Follow the
[installation guide](products/deployment-kit/docs/prebuilt/install.md) for commands.
You only need unzip support and a SHA-256 utility to install the package.

Choose a hosting path:

- [GitLab Pages](products/deployment-kit/docs/prebuilt/deploy-gitlab-pages.md): copy
  the complete package, including hidden files, and configure `PAGES_RUNNER_TAG`
  for an available Linux runner that can pull the selected job image.
- [Another static host](products/deployment-kit/docs/prebuilt/deploy-static-hosting.md):
  serve the complete `public/` directory at a domain root or URL prefix.

For a CI test build, download the `static-site` artifact ZIP from a successful
[CI run](https://github.com/Code-dot-mil/SkLC/actions/workflows/ci.yml). Unzip it once
to get the same package layout as a release. It is a preview,
not a published product release. See [CI package details](CI.md#github-validation).

The developer setup below is for working on the source.

## Download the skill catalog

Download `skill-catalog-<version>.zip` from
[GitHub Releases](https://github.com/Code-dot-mil/SkLC/releases), compare its SHA-256
with the digest GitHub displays for that asset, then unzip it once. The archive
contains the developer skill folders, their supporting files, and a
[short installation README](products/skill-catalog/README.md). Copy the folders
into your workspace's `.agents/skills/`. For PR testing, the `skill-catalog.zip` CI
artifact contains the same layout.

## Assess a local skill

The [assessment kit](products/assessment-kit/README.md) provides a standalone
`skill-assessment` CLI with `validate`, `advise`, and `assess` commands.
Install its wheel from an SkLC release without the checkout or site tooling;
compare its SHA-256 with the GitHub asset digest, then follow the assessment kit
installation and usage guide.

## Direction and current operation

The [roadmap](docs/roadmap.md) describes the intended assessment, catalog, and deployment products.

The current site builds from skill packages and existing tracked evidence:

1. Skills live under `skills/<namespace>/<skill-id>/`, with metadata and instructions in `SKILL.md`.
2. Python validates exchange metadata, checks existing BOE against exact skill content, and creates site records and skill ZIPs.
3. Astro consumes those records and builds the static catalog.

Tracked BOE lives under `.exchange/generated/boe/`. Site generation does not run a scanner or create new BOE. Missing or invalid matching evidence fails generation. New assessment tooling is planned in the roadmap.

## Repository Map

- `.exchange/` stores exchange policy, display configuration, tags, categories, and generated catalog output.
- `.github/workflows/ci.yml` validates the codebase and builds preview catalog artifacts.
- `CI.md` documents validation, packaging, and release behavior.
- `CONTRIBUTING.md` explains how developers contribute to the exchange application, tooling, CI, and documentation.
- `docs/architecture.md` documents the current component, evidence, catalog-build, and CI flows.
- `docs/roadmap.md` defines the Q3 2026 target product, GitHub release, and downstream delivery plan.
- `GOVERNANCE.md` describes exchange roles and generated-output boundaries.
- `scripts/skill_exchange/` contains Python catalog and release tooling.
- `site/` contains the Astro static site.
- `skills/` contains skill packages included in the exchange.
- `tests/` contains Python tests for exchange tooling and CI behavior.

## Developer Setup

Install the local toolchain:

- Python 3.12 with `uv`.
- Node.js 22 with `npm`.
- `just` for cross-stack commands.

Install dependencies:

```sh
uv sync --extra test
npm ci --prefix site
```

## Local Workflow

Run the common local checks:

```sh
just ci-local
```

Generate local catalog data from tracked evidence:

```sh
just generate
```

Build the static site from freshly generated local data:

```sh
just build
```

Select existing LLM-assisted evidence when available:

```sh
just generate llm-assisted
just build llm-assisted
```

The mode selects existing evidence; it does not start a scan.

Local `just` generation writes to `.exchange/local-generated/` so developers do not accidentally rewrite tracked CI-produced BOE. Use `uv` directly for Python-only checks and `npm --prefix site` for site-only checks. `just` is the local developer wrapper when a task intentionally spans both stacks.

Use [CONTRIBUTING.md](CONTRIBUTING.md) for exchange-site development workflow details.

## CI Workflow

- `CI` runs lint and tests, reads verified tracked BOE, builds the site, and uploads catalog artifacts.
- GitHub Dependabot owns dependency-vulnerability alerts and remediation pull requests.

See [CI.md](CI.md) for the full configuration reference.

## Configuration

Configuration is part of the portability model. Do not hardcode network-specific values into the repository. Use CI variables or environment variables for:

- Python and Node image registry, repository, tag, or full image override.
- Customer GitLab runner tags for packaged Pages deployment.

Secrets should be configured as masked CI variables in the target environment and must not be committed.

## Current Boundaries

This is a static exchange MVP. It does not implement a live application server, interactive approval workflow, protected-branch administration, hosting-provider API simulation, or user account model. Those responsibilities belong to the hosting platform and future exchange services.

## Operator kit

Use `deployment-kit-operator-<version>.zip` to assess a catalog and deploy its exchange
in GitLab. See the [operator guide](products/deployment-kit/docs/operator/README.md).
