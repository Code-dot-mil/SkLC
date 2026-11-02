# Skill Exchange Site

Skill Exchange Site serves assessed agent skills. Browse names and descriptions, read full instructions, and download a skill. Open an assessment for required remediation, unresolved findings, false positives, scope, and limitations, with downloads of the original report pair. The separate skill catalog can be installed without assessment or hosting tools.

The prebuilt kit serves four developer skills as a static introduction. The Operator kit can assess and serve a consumer's own skills. Product source and release composition follow [product boundaries](docs/product-boundaries.md).

## Use the prebuilt site

The prebuilt deployment kit contains an already-built site. Download `deployment-kit-prebuilt-<version>.zip` from [GitHub Releases](https://github.com/Code-dot-mil/SkLC/releases), compare its SHA-256 with the digest GitHub displays for that asset, then unzip it once. Follow the [installation guide](products/deployment-kit/prebuilt/docs/install.md) for commands. You only need unzip support and a SHA-256 utility to install the package.

Choose a hosting path:

- [GitLab Pages](products/deployment-kit/prebuilt/docs/deploy-gitlab-pages.md): copy the complete package, including hidden files, and configure `PAGES_RUNNER_TAG` for an available Linux runner that can pull the selected job image.
- [Another static host](products/deployment-kit/prebuilt/docs/deploy-static-hosting.md): serve the complete `public/` directory at a domain root or URL prefix.

For a CI test build, download the `static-site` artifact ZIP from a successful [CI run](https://github.com/Code-dot-mil/SkLC/actions/workflows/ci.yml). Unzip it once to get the same package layout as a release. It is a preview, not a published product release. See [CI package details](CI.md#github-validation).

The developer setup below is for working on the source.

## Download the skill catalog

Download `skill-catalog-<version>.zip` from [GitHub Releases](https://github.com/Code-dot-mil/SkLC/releases), compare its SHA-256 with the digest GitHub displays for that asset, then unzip it once. The archive contains the developer skill folders, their supporting files, and a [short installation README](products/skill-catalog/README.md). Copy the folders into your workspace's `.agents/skills/`. For PR testing, the `skill-catalog.zip` CI artifact contains the same layout.

## Assess a local skill

The [assessment kit](products/assessment-kit/README.md) provides a standalone `skill-assessment` CLI with `validate`, `hash`, `assess`, and `summarize` commands. Summarize explains remediation, unresolved findings, and false positives from existing paired reports. Install its wheel from an SkLC release without the checkout or site tooling; compare its SHA-256 with the GitHub asset digest, then follow the assessment kit installation and usage guide.

## Current operation

The current site builds from skill packages and existing tracked evidence:

1. Skills live under `products/skill-catalog/<skill-id>/`, with metadata and instructions in `SKILL.md`.
2. Python validates skill content, checks current adjudicated assessments against exact skill content, and creates site records and skill ZIPs.
3. Astro consumes those records and builds the static catalog.

Current reports live under `products/skill-catalog-assessments/<skill-name>/`. Site generation requires paired native findings and completed adjudication for the exact skill content. Generation is read-only and runs no scanner. Nonfatal partial coverage and negative safety judgments remain visible advisory results.

The `skill-catalog-assessments-<version>.zip` release download contains the current JSON pair for each of the four catalog skills, with its interpretation guide. Developers can use `skill-assessment summarize` to review required remediation, unresolved findings, false positives, scope, and limitations.

## Repository Map

- `.exchange/` contains derived local and CI catalog output.
- `.github/workflows/ci.yml` validates the codebase and builds preview catalog artifacts.
- `CI.md` documents validation, packaging, and release behavior.
- `CONTRIBUTING.md` explains how developers contribute to the exchange application, tooling, CI, and documentation.
- `docs/architecture.md` documents the current component, evidence, catalog-build, and CI flows.
- `docs/decisions.md` records accepted product and assessment decisions.
- `GOVERNANCE.md` describes exchange roles and generated-output boundaries.
- `products/deployment-kit/operator/` owns the Python catalog runtime, its tests, and the site build.
- `maintainer/` owns upstream packaging, release orchestration, and their tests.
- `products/deployment-kit/operator/site/` contains the Astro static site.
- `products/skill-catalog/` contains skill packages included in the exchange.
- `products/skill-catalog-assessments/` contains the current assessment pair for each catalog skill.
- `products/assessment-kit/` owns the standalone assessment CLI and its tests.

## Developer Setup

Install the local toolchain:

- Python 3.12 with `uv`.
- Node.js 22.23.4 or a newer Node 22 patch with `npm`.
- `just` for cross-stack commands.
- `actionlint` and `shellcheck` for workflow checks; see the [linting guide](docs/linting.md) for installation.

Install dependencies:

```sh
uv sync --extra test --group lint
npm ci
npm ci --prefix products/deployment-kit/operator/site
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

Local `just` generation writes to `.exchange/local-generated/` while current assessment reports remain read-only. Use `uv` directly for Python-only checks and `npm --prefix products/deployment-kit/operator/site` for site-only checks. `just` is the local developer wrapper when a task intentionally spans both stacks.

Use [CONTRIBUTING.md](CONTRIBUTING.md) for exchange-site development workflow details.

## CI Workflow

- `CI` runs lint and tests, assesses selected trusted PR changes, and maintains main-branch assessment evidence. Separate generation and build jobs consume current assessments without provider calls and upload product previews.
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

Use `deployment-kit-operator-<version>.zip` to assess a catalog and deploy its exchange in GitLab. See the [operator guide](products/deployment-kit/operator/docs/README.md).
