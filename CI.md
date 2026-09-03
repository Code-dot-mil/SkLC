# Skill Exchange CI

The repository owns GitHub validation in `.github/workflows/ci.yml` and GitLab CI in `.gitlab-ci.yml`.

## GitHub Validation

The `CI` workflow runs on every pull request targeting `main` and every push to `main`. GitHub-hosted Ubuntu runners execute the Python and site lint and test commands defined by the local `Justfile`; any failed command blocks the final artifact job. A Python producer checks out full history, derives site data and skill downloads only from successful exact-current-content tracked BOE, and cannot invoke SkillSpector or an LLM. Repository and immutable commit context from the pull-request head or push override the placeholder site configuration so generated source links target the revision being built, including for fork pull requests. The Node.js consumer downloads that data, builds `site/dist/`, verifies that the catalog, detail pages, and skill downloads are present, and uploads the downloadable `static-site` zip artifact.

Reuse-only generation intentionally fails when a valid skill lacks successful exact-current-content tracked BOE. Until a protected GitHub publication workflow supplies that evidence, new or changed skills cannot produce the static-site artifact in this workflow.

## GitLab Pipeline Shape

- `lint`, `test`, and `audit` run for merge requests and default-branch pushes when site code, exchange tooling, tests, or CI configuration changes.
- `review:skills` runs only for merge requests that change `skills/**/*`. It validates changed skill packages, runs [NVIDIA SkillSpector](https://github.com/NVIDIA/SkillSpector), writes reviewer artifacts, and can post a merge request comment when comment variables are configured.
- `publish:exchange` runs for scheduled pipelines and default-branch push pipelines that change `skills/**/*`. It generates the full `.exchange/generated/` tree for deploy artifacts and commits BOE bundles back when bot push variables are configured.
- `generate:exchange` runs on default-branch push pipelines that do not change `skills/**/*`. It generates deploy-time `.exchange/generated/` artifacts without committing them.
- `pages` runs on default-branch push pipelines and scheduled pipelines. It deploys from generated exchange artifacts produced by `generate:exchange` or `publish:exchange` in the same pipeline.
- Python publication jobs reuse tracked BOE bundles when the computed scan cache key already exists. Runner caches are used for dependencies only, not as the source of scanner history.
- Non-Pages jobs use the runner tag in `SKLC_RUNNER_TAG`.
- `pages` uses the runner tag in `PAGES_RUNNER_TAG`.
- By default, Python jobs use the official Docker Hub Python image and install `uv` with `PYTHON_BOOTSTRAP_COMMAND`. Override the image variables when the target environment requires an internal registry or a prebuilt image.

The checked-in runner tag defaults are environment examples. Override them in the destination GitLab project instead of editing job definitions.

## Dependency Vulnerability Management

GitHub Dependabot is the authoritative dependency-vulnerability control. Dependabot alerts and security updates must remain enabled in repository settings, and GitHub Security is the only alert backlog; do not create a scheduled CI job that duplicates it.

`.github/dependabot.yml` covers the root `pyproject.toml` and `uv.lock` with the `uv` ecosystem and `site/package.json` and `site/package-lock.json` with the `npm` ecosystem. Version updates run weekly on Monday. Minor and patch updates are grouped per ecosystem, while major updates remain separate. Dependabot uses its default dependency and ecosystem labels and assigns update pull requests to `Fnorgh2`.

`Fnorgh2` owns alert triage and must receive GitHub notifications for high- and critical-severity alerts. High and critical alerts are reviewed when received; the remaining backlog is reviewed weekly. Alerts that cannot be remediated promptly are escalated to repository administrator `scotluns`. The legacy `.gitlab-ci.yml` is not an active dependency-vulnerability control for this GitHub repository.

## Required Schedule

Create a GitLab pipeline schedule for the default branch using the cadence required by the target environment, such as nightly. The schedule should run with `CI_PIPELINE_SOURCE=schedule`, which triggers `publish:exchange` followed by `pages`.

Merges to the default branch that add or update skills also trigger `publish:exchange` before `pages`. That keeps the first deploy of a changed skill aligned with committed BOE instead of relying on a later scheduled backfill.

Avoid duplicating project-level CI variables on the schedule unless the schedule intentionally needs a different value. GitLab schedule variables override project variables, so a stale schedule value can silently change publication behavior. In particular, keep `SKLC_PUBLISH_SCAN_MODES` aligned with the desired official publication modes.

For official BOE publication, run the schedule as the exchange bot or provide bot credentials through masked CI variables.

The target GitLab project also needs shared or project runners enabled for the configured tags, GitLab Pages available for the `pages` job, and permission for the publication identity to push BOE commits. `publish:exchange` defaults `EXCHANGE_PUBLISH_COMMIT=true` so official publication fails before deploy rather than publishing a skill whose BOE cannot be persisted. Override it only when another controlled process persists BOE.

## Publish Authentication

Keep merge request review credentials separate from publication credentials. The token named by `SKLC_REVIEW_TOKEN_VARIABLE` is used only for optional merge request comments. It is not used to push BOE commits.

`publish:exchange` chooses push credentials in this order:

1. `EXCHANGE_PUBLISH_PUSH_URL`, when a complete authenticated remote URL is provided.
2. `EXCHANGE_PUBLISH_TOKEN` with `EXCHANGE_PUBLISH_USERNAME`, when an explicit publisher token is configured.
3. `CI_JOB_TOKEN` with username `gitlab-ci-token`, when GitLab job-token repository push is enabled.

For the default `CI_JOB_TOKEN` path, enable the GitLab project setting that allows CI job tokens to push to the repository, then ensure the pipeline identity is permitted to push to the protected default branch. For a protected `main`, that usually means the branch allows Maintainer pushes and the scheduled or default-branch pipeline runs under a Maintainer-capable identity.

If the destination project cannot allow job-token pushes to the protected branch, configure a masked `EXCHANGE_PUBLISH_TOKEN` for a dedicated publisher identity with the minimum repository write scope supported by that GitLab instance. The publisher identity must be allowed to push to the protected default branch. Do not reuse the merge request comment token for publication.

## Configurable Variables

All environment-specific values are CI variables:

- `PYTHON_IMAGE_REGISTRY`, `PYTHON_IMAGE_REPOSITORY`, `PYTHON_IMAGE_TAG`, and `PYTHON_IMAGE` select the Python runner image.
- `PYTHON_BOOTSTRAP_COMMAND` installs Python job prerequisites when the selected image does not already include them. Set it to an empty string when using a prebuilt image with `uv` installed.
- `NODE_IMAGE_REGISTRY`, `NODE_IMAGE_REPOSITORY`, `NODE_IMAGE_TAG`, and `NODE_IMAGE` select the Node runner image.
- `SKLC_RUNNER_TAG` selects the runner tag for lint, test, audit, review, and publish jobs.
- `PAGES_RUNNER_TAG` selects the GitLab Pages runner tag.
- `SKILLSPECTOR_INSTALL_COMMAND` installs SkillSpector when the runner image does not already include it.
- `SKILLSPECTOR_BIN` points to a SkillSpector binary when it is not on `PATH`.
- `SKLC_REVIEW_SCAN_MODE` controls MR review scanning: `static-only` or `llm-assisted`.
- `SKLC_PUBLISH_SCAN_MODES` controls official publication scanning, using comma or space separated modes. Use `static-only,llm-assisted` when official publication should include both static and LLM-backed BOE.
- `SKLC_LLM_API_KEY`, `SKLC_LLM_BASE_URL`, `SKLC_LLM_MODEL`, and `SKLC_LLM_PROVIDER` configure LLM-assisted scans without tying the repository to a specific provider.
- `SKLC_POST_REVIEW_COMMENT`, `SKLC_REVIEW_TOKEN_VARIABLE`, and `SKLC_REVIEW_TOKEN_HEADER` control optional merge request comments.
- `EXCHANGE_PUBLISH_COMMIT`, `EXCHANGE_PUBLISH_PUSH`, `EXCHANGE_PUBLISH_BRANCH`, `EXCHANGE_PUBLISH_PUSH_URL`, `EXCHANGE_PUBLISH_TOKEN`, and `EXCHANGE_PUBLISH_USERNAME` control BOE-bundle commits. When GitLab job-token repository push is enabled and no publish token is configured, publication uses `CI_JOB_TOKEN` with the `gitlab-ci-token` username.
- `EXCHANGE_BOT_GIT_NAME`, `EXCHANGE_BOT_GIT_EMAIL`, and `EXCHANGE_PUBLISH_COMMIT_MESSAGE` control generated commit metadata.
- Provider credentials and endpoints for LLM-assisted SkillSpector scans should be configured as masked CI variables, not committed to the repository.

When the same skill content, SkillSpector version, scan mode, and scanner configuration have already produced BOE, scheduled publication should report reused scans and avoid committing new BOE. The first LLM-assisted publication for a cache key creates LLM-backed BOE; later runs with the same key should reuse it.
