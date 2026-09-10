# Catalog Assessment Automation Spec

## Decision baseline

This spec follows `docs/decisions.md`: maintainer automation runs from GitHub and must not become customer GitLab CI or a separate product.

## Milestone

`docs/roadmap.md` section 3.6, Deferred internal milestone - Catalog assessment automation.

## Status

Draft.

An agent must not execute this spec until a human reviewer changes this status
to Approved.

## Outcome

SkLC maintainers use the in-repository assessment kit to advise on proposed catalog skill changes and maintain assessment records for the initial catalog.

## Release impact

This milestone is internal enabling work. It is not Q3 MVP work unless BOE becomes required for an accepted catalog release.

## Scope

Included:

- GitHub Actions that run the assessment-kit implementation from the current checkout.
- Advice on proposed catalog skill changes in pull requests.
- Post-merge assessment for catalog skill changes on `main`.
- Maintainer runner configuration for jobs that require assessor access.
- Source-controlled native assessor reports and BOE manifests for the initial catalog under `boe/`.

## Contracts

The automation consumes the in-repository assessment-kit implementation, skill-package contract, release-manifest contract, and BOE-manifest contract. It does not define customer-facing contracts.

## Assessment-kit source

This is maintainer automation for the repository that contains both the catalog
source and the assessment-kit source. Workflows use the assessment-kit code from
the current GitHub Actions checkout. They do not download an assessment-kit
release, select an external assessment-kit repository, or verify assessment-kit
release artifacts before invoking `validate`, `advise`, `assess`, or
`verify-boe`.

`setup-assessment-kit` is a workflow setup job or step, not a released product,
downloadable artifact, or reusable CI component. It installs repository
dependencies for the checked-out revision and confirms the CLI entry point works
before downstream jobs invoke it:

```text
uv run skill-assessment --help
```

Each job that invokes `skill-assessment` performs its own checkout and setup.
Jobs must not depend on runner-local Python environments, release artifacts, or
workflow artifacts as proof that the assessment kit is available.

## GitHub Actions

Implement these maintainer workflows and job names:

| Workflow | Trigger | Jobs | Source-control writes |
|---|---|---|---|
| `catalog-assessment-advice` | `pull_request` with types `opened`, `reopened`, `synchronize`, and `ready_for_review`; path scope `skills/**`; skipped for draft pull requests | `detect-changed-skills`, `setup-assessment-kit`, `advise-changed-skills` | None |
| `catalog-assessment-post-merge` | `push` to `main`; path scope `skills/**`; skip when the changed files are only under `boe/**` | `detect-changed-skills`, `setup-assessment-kit`, `assess-catalog-skills`, `verify-boe`, `persist-catalog-boe` | BOE bundles only |
| `catalog-assessment-manual` | `workflow_dispatch` with `mode` of `advise` or `assess` and optional newline-separated `skill_paths` | `select-skills`, `setup-assessment-kit`, `run-selected-assessment`, `verify-boe` when `mode` is `assess` | None by default |

`detect-changed-skills`, `setup-assessment-kit`, `select-skills`, and `verify-boe` run on GitHub-hosted Linux runners. Jobs that invoke an assessor with protected credentials, including `advise-changed-skills`, `assess-catalog-skills`, and assessor-backed `run-selected-assessment`, run on an approved maintainer runner selected by repository variable `SKLC_CATALOG_ASSESSOR_RUNNER_LABELS_JSON`. The workflow fails closed when that variable is unset for a job that requires assessor access. Static validation must not be routed to the maintainer assessor runner.

`SKLC_CATALOG_ASSESSOR_RUNNER_LABELS_JSON` is a JSON array of GitHub
Actions runner labels, for example `["self-hosted","linux","skill-assessment"]`.
Protected assessor jobs use this exact expression:

```yaml
runs-on: ${{ fromJSON(vars.SKLC_CATALOG_ASSESSOR_RUNNER_LABELS_JSON) }}
```

The workflow validates the variable before protected jobs run: it must parse as
a non-empty JSON array of non-empty strings. The labels are
maintainer-controlled metadata, not customer configuration.

## Assessor configuration

Protected assessor jobs pass model credentials through environment variables
only. For SkillSpector, `SKLC_LLM_API_KEY`,
`SKLC_LLM_BASE_URL`, `SKLC_LLM_MODEL`, and
`SKLC_LLM_PROVIDER` are passed to the checked-out assessment CLI when
`llm-assisted` scanning is selected. For the first release, all four are
required and `SKLC_LLM_PROVIDER` must be `openai_compatible`. These values must
not be written to workflow artifacts, job summaries, or committed files.

`SKLC_SKILLSPECTOR_SCAN_MODE` is the assessment-kit environment variable for
scan mode and defaults to `llm-assisted`. Supported values are `llm-assisted`
and explicit `static-only`. When `llm-assisted` is selected or defaulted, the
protected assessor job fails closed before invoking the assessment CLI unless
the required `SKLC_LLM_*` variables are available in the job environment and
the provider value is supported. The workflow must not fall back to
`static-only` when `llm-assisted` is selected or defaulted but its required
environment variables are unavailable.

## BOE persistence credentials

Post-merge BOE persistence uses one maintainer repository secret for push
authentication:

| Secret | Purpose |
|---|---|
| `SKLC_CATALOG_BOE_PUSH_TOKEN` | Fine-grained token allowed to push BOE-only commits to the maintainer repository. |

Commit author identity is configured separately from push authentication:

| Variable | Default | Purpose |
|---|---|---|
| `SKLC_CATALOG_BOE_COMMIT_NAME` | `skill-exchange-bot` | Git `user.name` for BOE-only evidence commits. |
| `SKLC_CATALOG_BOE_COMMIT_EMAIL` | `skill-exchange-bot@example.invalid` | Git `user.email` for BOE-only evidence commits. |

`persist-catalog-boe` configures Git with the configured author name and email,
uses `SKLC_CATALOG_BOE_PUSH_TOKEN` only for the push remote, and must
not print the token or write it to artifacts. The token controls push
authorization and may determine the authenticated pusher recorded by the hosting
platform, but it does not replace the explicit Git commit author identity. The
token must not have permission to edit repository settings, releases, variables,
secrets, or protected branch rules. The job fails closed when the push token is
missing.

## Changed-skill detection

- A changed skill is any directory below `skills/` that contains `SKILL.md` and has any tracked file added, modified, renamed, copied, or deleted below that directory.
- Pull-request detection compares the pull request base SHA to the pull request head SHA.
- Post-merge detection compares `github.event.before` to `github.sha`. If the previous SHA is unavailable, the workflow selects every catalog skill under `skills/`.
- Manual detection uses `skill_paths` when provided; otherwise it selects every catalog skill under `skills/`.
- Detection emits a JSON matrix of existing changed skill package paths. Deleted skills are reported in the job summary but are not passed to `advise` or `assess`.
- Changes under `boe/**`, catalog policy, site files, CI files, documentation, or contracts do not select skills for this milestone unless a skill package under `skills/` also changed.

## Advice behavior

For pull requests, `advise-changed-skills` runs the checked-out assessment kit with repeated `--skill <path>` arguments for the detected existing skill packages. It publishes job artifacts containing native assessor reports and author-facing advice. It must not create or commit BOE, edit catalog policy, decide publication, or publish pull-request comments unless a later milestone explicitly adds that behavior.

Command template:

```text
uv run skill-assessment validate --skill <changed-skill-path> [--skill <changed-skill-path> ...]
uv run skill-assessment advise \
  --skill <changed-skill-path> [--skill <changed-skill-path> ...] \
  --assessor skillspector \
  --output .exchange/generated/advice/<pull-request-number>
```

The advice artifact path is
`.exchange/generated/advice/<pull-request-number>/`. It is retained as a
workflow artifact only and must not be committed.

## Post-merge assessment behavior

For `push` events on `main`, `assess-catalog-skills` runs the checked-out assessment kit with repeated `--skill <path>` arguments for the detected existing skill packages. It retains the assessor's native output unchanged and updates BOE manifests. `verify-boe` must run against every BOE manifest produced by the job before any persistence step.

Command template:

```text
uv run skill-assessment validate --skill <changed-skill-path> [--skill <changed-skill-path> ...]
uv run skill-assessment assess \
  --skill <changed-skill-path> [--skill <changed-skill-path> ...] \
  --assessor skillspector \
  --boe-root boe
```

The post-merge workflow verifies BOE with this mapping:

```text
for each assessed skill path:
  skill_name = basename(skill path)
  uv run skill-assessment verify-boe --skill <skill path> "boe/<skill_name>"
```

The job fails when an assessed skill has no matching BOE directory or
`verify-boe` exits non-zero.

The workflow configures scan mode with `SKLC_SKILLSPECTOR_SCAN_MODE` in the job
environment. It does not generate an assessment-kit config file from repository
variables.

## Report and BOE storage

Formal post-merge assessment output is stored as BOE bundles under:

```text
boe/
  <skill-name>/
    boe.json
    assessments/
      <assessor-id>/
        <raw-report-sha256>.json
```

`<skill-name>` is the standard skill name from the skill-package contract. Report filenames and BOE entries follow the assessment kit's `--boe-root` layout. `boe.json` must conform to the BOE-manifest contract and list report paths relative to its own directory.

Pull-request advice output is retained only as workflow artifacts using the same skill-relative path and run key shape. Advice artifacts are not source-controlled BOE.

## Post-merge persistence rules

- `persist-catalog-boe` runs only on `push` to `main`, only after `verify-boe` succeeds, and only when `SKLC_CATALOG_BOE_PUSH_TOKEN` is configured.
- The persistence step may add or update files only under `boe/**`.
- If assessment produces no BOE changes, the workflow exits successfully without a commit.
- The evidence commit message uses `chore(catalog): update BOE for assessed skills` and records the assessed source commit in the commit body.
- A BOE-only evidence commit must not trigger a new assessment run.
- A missing push token leaves the verified BOE as workflow artifacts and fails the persistence job; that state is not accepted as milestone completion.
- Persistence must not edit skill packages, catalog policy, release manifests, site output, or customer CI.

## Evidence

Acceptance requires maintainer workflows that:

1. Set up and run the assessment-kit implementation from the current checkout.
2. Detect changed catalog skills and run advice without creating BOE or changing catalog policy.
3. Run post-merge assessment on catalog skill changes that reach `main`.
4. Store native reports and BOE bundles under `boe/`.
5. Verify every stored BOE with the checked-out `verify-boe` command.

## Non-Q3 and deferred conditions

This work remains deferred when any of these conditions hold:

- BOE is not required for the accepted initial catalog release.
- The current checkout does not provide working `advise`, `assess`, and `verify-boe` commands.
- An approved maintainer runner with required assessor access is not available or `SKLC_CATALOG_ASSESSOR_RUNNER_LABELS_JSON` is invalid.
- `SKLC_CATALOG_BOE_PUSH_TOKEN` for post-merge BOE persistence is not configured.
- The requested outcome is customer GitLab CI, operator deployment, automated publication, pull-request comments, or catalog-policy automation rather than maintainer-only catalog assessment.

## Exclusions

- Customer GitLab CI.
- Operator deployment.
- Automated publication decisions.
- Catalog-policy changes.
- Repository-private assessment interfaces.
