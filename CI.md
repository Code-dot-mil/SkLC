# Skill Exchange CI

The repository owns GitHub validation in `.github/workflows/ci.yml`, protected SkillSpector review and publication in `.github/workflows/skillspector.yml`, and the legacy GitLab pipeline in `.gitlab-ci.yml`.

## GitHub Validation

The `CI` workflow runs on every pull request targeting `main` and every push to `main`. GitHub-hosted Ubuntu runners execute the Python and site lint and test commands defined by the local `Justfile`; any failed command blocks the final artifact job. A Python producer checks out full history, reuses successful exact-current-content tracked BOE, and runs pinned upstream SkillSpector 2.10.0 in static-only mode when preview evidence is missing. Repository and immutable commit context from the pull-request head or push override the placeholder site configuration so generated source links target the revision being built, including for fork pull requests. This preview generation never uses an LLM and never commits BOE. The Node.js consumer downloads the generated data and builds `site/dist/`.

The final artifact job then sets up Python 3.12 and runs the prebuilt release
builder against that site output. It extracts the resulting archive and runs the
included `scripts/verify_prebuilt.py`, with an expected-version check, before
checking that catalog detail pages and skill ZIPs are present. Only that verified
package root is uploaded as the downloadable `static-site` ZIP, including hidden
files such as `.gitlab-ci.yml`. Extracting the ZIP gives `public/`, documentation,
the deployment job, vendored schema, verifier, manifest, and checksums together;
it does not give bare website files or another archive to unpack.

CI uses the test-only version `0.0.0-ci.<run-id>.<run-attempt>` and records
`github.sha` as the source revision: the checked-out PR merge commit or push
commit. This job creates no tag or GitHub Release and selects no product release
version. Packaging and extraction use a fresh directory under `RUNNER_TEMP`.
Any build, extraction, verification, or required-content failure prevents upload.

## GitHub SkillSpector Workflow

The `SkillSpector` workflow replaces the GitLab-specific private scanner installation and publication jobs:

- Pull requests that change `skills/**` run package validation and SkillSpector review. Same-repository pull requests use the configured OpenAI-compatible gateway and receive the generated review as a pull request comment. Fork pull requests explicitly use static-only review because GitHub does not provide repository secrets to fork workflows; their artifacts are retained but no comment is posted because their workflow tokens are read-only. Review output is also added to the job summary and retained as a workflow artifact; it is advisory and is never committed as official evidence.
- Pushes to `main` that change `skills/**`, the nightly schedule, and manual dispatches run official `static-only,llm-assisted` publication.
- Publication installs upstream SkillSpector 2.10.0 through the locked `scan` dependency extra, pinned to NVIDIA's immutable `v2.10.0` Git commit because that release is not available from PyPI. No custom SkillSpector fork, model proxy, or model container is required.
- Publication commits only `.exchange/generated/boe/` and pushes it to the default branch with the job-scoped `GITHUB_TOKEN`. Full generated output and `publish-result.json` are retained as workflow artifacts.
- Exact tracked BOE cache keys are reused. Gateway endpoint identity is represented in the cache configuration by a SHA-256 digest; the endpoint and API key are not written to BOE.

Configure these GitHub repository settings before enabling the workflow:

| Kind | Name | Value |
|---|---|---|
| Actions secret | `SKILL_EXCHANGE_LLM_API_KEY` | OpenAI-compatible gateway API key |
| Actions variable | `SKILL_EXCHANGE_LLM_PROVIDER` | `openai_compatible` |
| Actions variable | `SKILL_EXCHANGE_LLM_BASE_URL` | `https://mdevchat.apim.mitre.org/openai/v1` |
| Actions variable | `SKILL_EXCHANGE_LLM_MODEL` | `gpt-5.5` |
| Actions variable | `SKILL_EXCHANGE_LLM_API_KEY_HEADER` | Gateway-defined HTTP header that carries the API key, such as `Ocp-Apim-Subscription-Key` |
| Actions variable | `RUNNER_CA_BUNDLE_PATH` | Absolute path, on each self-hosted runner, to a readable PEM bundle containing the enterprise TLS CA chain |

For gateways that authenticate an OpenAI-compatible API with a nonstandard API-key header, the repository adapter passes the configured `SKILL_EXCHANGE_LLM_API_KEY` value in `SKILL_EXCHANGE_LLM_API_KEY_HEADER`. The header name is explicit and included in the scanner cache configuration; the credential is never written to BOE.

The self-hosted workflow passes `RUNNER_CA_BUNDLE_PATH` to Node as `NODE_EXTRA_CA_CERTS` before `actions/setup-python` starts and to Python as `SSL_CERT_FILE`. This allows Node-based actions and the Python CI helper that posts review comments to trust the enterprise TLS CA chain without disabling certificate verification. The workflow fails before Python setup if the variable is unset or the bundle is unreadable. The bundle must be present in the runner execution environment, including the runner container when one is used.

The repository or organization Actions policy must allow `GITHUB_TOKEN` write access, and the `main` branch ruleset must allow the GitHub Actions publication identity to push the generated-evidence commit. The review job requests `pull-requests: write` only to add its generated review comment for same-repository pull requests; the publication job requests only `contents: write`. If branch policy forbids direct bot pushes, configure an equivalent ruleset bypass for the publication workflow before running it. Do not replace `GITHUB_TOKEN` with the LLM gateway credential or reuse the gateway credential for repository access.

## Prebuilt Releases

`.github/workflows/release.yml` runs when a maintainer pushes a `v<version>` tag.
Tag creation is the release approval action: complete the human-reviewed checklist
in `docs/specs/release-process.md`, including clean GitLab Pages acceptance proof,
before tagging. This workflow does not create tags or approve release readiness.
Only `deployment-kit-prebuilt` is packaged in this first release implementation;
standalone catalog packaging belongs to its follow-up PR.

The tagged commit must contain exactly one nonempty `## <version>` section in
`RELEASE_NOTES.md`. The workflow rejects invalid versions, missing/duplicate/empty
notes, untracked or modified notes, and a checkout that does not match the tag.
Fenced Markdown examples do not count as release headings. The accepted section
becomes the release body, not a separate downloadable asset.

After Python and site checks, the workflow regenerates the site data using only
exact-content tracked BOE, builds the site, and uses the same prebuilt builder and
shipped verifier as ordinary CI. Missing evidence fails without running a scanner.
It extracts and verifies the package and checks the external checksum file before
publishing. Temporary output stays under `RUNNER_TEMP`; source revision and
repeatable archive timestamps come from the tagged commit.

The GitHub Release contains exactly the prebuilt `.tar.gz`, the external
`release-manifest.json`, and `SHA256SUMS.txt`. `gh release create --verify-tag`
requires the tag to exist and does not overwrite an existing release. SemVer
prereleases are marked as GitHub prereleases. Checkout does not persist Git
credentials, and `GH_TOKEN` is exposed only to the publishing step. The job uses
GitHub-hosted Ubuntu, a 30-minute timeout, and per-tag concurrency without cancelling
an in-progress release.

## Prebuilt Consumer Verification

The deployment-only template at
`products/deployment-kit/ci/gitlab/prebuilt/.gitlab-ci.yml` consumes a complete
prebuilt release package, not a flat site build. Its Linux runner must support
job images and match the configured `PAGES_RUNNER_TAG`. The `pages` job selects
`$PYTHON_IMAGE`, defaulting to the official `python:3.12-slim` image, rather than
relying on Python being installed in the runner's default image. The runner must
be allowed to pull that image. Override `PYTHON_IMAGE_REGISTRY`,
`PYTHON_IMAGE_REPOSITORY`, `PYTHON_IMAGE_TAG`, or the complete `PYTHON_IMAGE`
through project/group CI/CD variables when an internal registry is required.
An override must provide a POSIX shell and `python3` running Python 3.12 or newer.
The `pages` job runs `python3 -I -S scripts/verify_prebuilt.py .`, the same offline
verification command documented in the package installation guide. It checks
manifest/schema consistency, file checksums, required contents, safe paths, and
referenced downloads before publishing the unchanged `public/` directory.
The verification script does not install dependencies, fetch inputs, build a site,
or run assessments. Python is not needed to serve the published static files.
The `static-site` CI download uses this same complete package layout and verifier;
it is a CI test build, not a published product release.

## GitLab Pipeline Shape

- `lint`, `test`, and `audit` run for merge requests and default-branch pushes when site code, exchange tooling, tests, or CI configuration changes.
- `review:skills` runs only for merge requests that change `skills/**/*`. It validates changed skill packages, runs [NVIDIA SkillSpector](https://github.com/NVIDIA/SkillSpector), writes reviewer artifacts, and can post a merge request comment when comment variables are configured.
- `publish:exchange` runs for scheduled pipelines and default-branch push pipelines that change `skills/**/*`. It generates the full `.exchange/generated/` tree for deploy artifacts and commits BOE bundles back when bot push variables are configured.
- `generate:exchange` runs on default-branch push pipelines that do not change `skills/**/*`. It generates deploy-time `.exchange/generated/` artifacts without committing them.
- `pages` runs on default-branch push pipelines and scheduled pipelines. It deploys from generated exchange artifacts produced by `generate:exchange` or `publish:exchange` in the same pipeline.
- Python publication jobs reuse tracked BOE bundles when the computed scan cache key already exists. Runner caches are used for dependencies only, not as the source of scanner history.
- Non-Pages jobs use the runner tag in `SKILL_EXCHANGE_RUNNER_TAG`.
- `pages` uses the runner tag in `PAGES_RUNNER_TAG`.
- By default, Python jobs use the official Docker Hub Python image and install `uv` with `PYTHON_BOOTSTRAP_COMMAND`. Override the image variables when the target environment requires an internal registry or a prebuilt image.

The checked-in runner tag defaults are environment examples. Override them in the destination GitLab project instead of editing job definitions.

## Dependency Vulnerability Management

GitHub Dependabot is the authoritative dependency-vulnerability control. Dependabot alerts and security updates must remain enabled in repository settings, and GitHub Security is the only alert backlog; do not create a scheduled CI job that duplicates it.

`.github/dependabot.yml` covers the root `pyproject.toml` and `uv.lock` with the `uv` ecosystem and `site/package.json` and `site/package-lock.json` with the `npm` ecosystem. Version updates run weekly on Monday. Minor and patch updates are grouped per ecosystem, while major updates remain separate. Dependabot uses its default dependency and ecosystem labels and assigns update pull requests to `Fnorgh2`.

`Fnorgh2` owns alert triage and must receive GitHub notifications for high- and critical-severity alerts. High and critical alerts are reviewed when received; the remaining backlog is reviewed weekly. Alerts that cannot be remediated promptly are escalated to repository administrator `scotluns`. The legacy `.gitlab-ci.yml` is not an active dependency-vulnerability control for this GitHub repository.

## Legacy GitLab Schedule

Create a GitLab pipeline schedule for the default branch using the cadence required by the target environment, such as nightly. The schedule should run with `CI_PIPELINE_SOURCE=schedule`, which triggers `publish:exchange` followed by `pages`.

Merges to the default branch that add or update skills also trigger `publish:exchange` before `pages`. That keeps the first deploy of a changed skill aligned with committed BOE instead of relying on a later scheduled backfill.

Avoid duplicating project-level CI variables on the schedule unless the schedule intentionally needs a different value. GitLab schedule variables override project variables, so a stale schedule value can silently change publication behavior. In particular, keep `SKILL_EXCHANGE_PUBLISH_SCAN_MODES` aligned with the desired official publication modes.

For official BOE publication, run the schedule as the exchange bot or provide bot credentials through masked CI variables.

The target GitLab project also needs shared or project runners enabled for the configured tags, GitLab Pages available for the `pages` job, and permission for the publication identity to push BOE commits. `publish:exchange` defaults `EXCHANGE_PUBLISH_COMMIT=true` so official publication fails before deploy rather than publishing a skill whose BOE cannot be persisted. Override it only when another controlled process persists BOE.

## Publish Authentication

Keep merge request review credentials separate from publication credentials. The token named by `SKILL_EXCHANGE_REVIEW_TOKEN_VARIABLE` is used only for optional merge request comments. It is not used to push BOE commits.

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
- `SKILL_EXCHANGE_RUNNER_TAG` selects the runner tag for lint, test, audit, review, and publish jobs.
- `PAGES_RUNNER_TAG` selects the GitLab Pages runner tag.
- `SKILLSPECTOR_INSTALL_COMMAND` installs SkillSpector when the runner image does not already include it.
- `SKILLSPECTOR_BIN` points to a SkillSpector binary when it is not on `PATH`.
- `SKILL_EXCHANGE_REVIEW_SCAN_MODE` controls MR review scanning: `static-only` or `llm-assisted`.
- `SKILL_EXCHANGE_PUBLISH_SCAN_MODES` controls official publication scanning, using comma or space separated modes. Use `static-only,llm-assisted` when official publication should include both static and LLM-backed BOE.
- `SKILL_EXCHANGE_LLM_API_KEY`, `SKILL_EXCHANGE_LLM_BASE_URL`, `SKILL_EXCHANGE_LLM_MODEL`, `SKILL_EXCHANGE_LLM_PROVIDER`, `SKILL_EXCHANGE_LLM_API_KEY_HEADER`, `SKILL_EXCHANGE_LLM_DEPLOYMENT`, and `SKILL_EXCHANGE_LLM_API_VERSION` configure LLM-assisted scans without using provider-specific exchange variable names.
- `SKILL_EXCHANGE_POST_REVIEW_COMMENT`, `SKILL_EXCHANGE_REVIEW_TOKEN_VARIABLE`, and `SKILL_EXCHANGE_REVIEW_TOKEN_HEADER` control optional merge request comments.
- `EXCHANGE_PUBLISH_COMMIT`, `EXCHANGE_PUBLISH_PUSH`, `EXCHANGE_PUBLISH_BRANCH`, `EXCHANGE_PUBLISH_PUSH_URL`, `EXCHANGE_PUBLISH_TOKEN`, and `EXCHANGE_PUBLISH_USERNAME` control BOE-bundle commits. When GitLab job-token repository push is enabled and no publish token is configured, publication uses `CI_JOB_TOKEN` with the `gitlab-ci-token` username.
- `EXCHANGE_BOT_GIT_NAME`, `EXCHANGE_BOT_GIT_EMAIL`, and `EXCHANGE_PUBLISH_COMMIT_MESSAGE` control generated commit metadata.
- Provider credentials and endpoints for LLM-assisted SkillSpector scans should be configured as masked CI variables, not committed to the repository.

When the same skill content, SkillSpector version, scan mode, and scanner configuration have already produced BOE, scheduled publication should report reused scans and avoid committing new BOE. The first LLM-assisted publication for a cache key creates LLM-backed BOE; later runs with the same key should reuse it.
