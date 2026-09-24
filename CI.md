# Skill Exchange CI

The repository owns GitHub validation in `.github/workflows/ci.yml`, protected SkillSpector review and publication in `.github/workflows/skillspector.yml`, and release publication in `.github/workflows/release.yml`.

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

The `SkillSpector` workflow owns protected scanner review and publication:

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
| Actions variable | `SKILL_EXCHANGE_LLM_API_KEY_HEADER` | Gateway-defined HTTP header that carries the API key, such as `api-key` |
| Actions variable | `SKILL_EXCHANGE_LLM_REQUESTS_PER_SECOND` | Maximum shared LLM request start rate; use `0.1` to serialize calls at ten-second intervals |
| Actions variable | `SKILL_EXCHANGE_LLM_MAX_OUTPUT_TOKENS` | Maximum output tokens requested per LLM call; use `2048` for the structured scanner responses |
| Actions variable | `SKILL_EXCHANGE_SCAN_MAX_SECONDS` | Per-skill scanner workflow budget; use `600` when gateway pacing can exceed SkillSpector's native budget |
| Actions variable | `RUNNER_CA_BUNDLE_PATH` | Absolute path, on each self-hosted runner, to a readable PEM bundle containing the enterprise TLS CA chain |

For gateways that authenticate an OpenAI-compatible API with a nonstandard API-key header, the repository adapter passes the configured `SKILL_EXCHANGE_LLM_API_KEY` value in `SKILL_EXCHANGE_LLM_API_KEY_HEADER`. The adapter also applies the explicit `SKILL_EXCHANGE_LLM_REQUESTS_PER_SECOND` rate across the pinned scanner's parallel analyzers, caps each request at `SKILL_EXCHANGE_LLM_MAX_OUTPUT_TOKENS`, and applies `SKILL_EXCHANGE_SCAN_MAX_SECONDS` to the per-skill workflow budget. These non-secret execution settings are included in the scanner cache configuration; the credential is never written to BOE.

The self-hosted workflow passes `RUNNER_CA_BUNDLE_PATH` to Node as `NODE_EXTRA_CA_CERTS` before `actions/setup-python` starts and to Python as `SSL_CERT_FILE`. This allows Node-based actions and the Python CI helper that posts review comments to trust the enterprise TLS CA chain without disabling certificate verification. The workflow fails before Python setup if the variable is unset or the bundle is unreadable. The bundle must be present in the runner execution environment, including the runner container when one is used.

The repository or organization Actions policy must allow `GITHUB_TOKEN` write access, and the `main` branch ruleset must allow the GitHub Actions publication identity to push the generated-evidence commit. The review job requests `pull-requests: write` only to add its generated review comment for same-repository pull requests; the publication job requests only `contents: write`. If branch policy forbids direct bot pushes, configure an equivalent ruleset bypass for the publication workflow before running it. Do not replace `GITHUB_TOKEN` with the LLM gateway credential or reuse the gateway credential for repository access.

## Skill Catalog Download

The independent `skill-catalog` job runs `scripts/package-skill-catalog.sh`.
It archives the selected skill folders and installation README from the
checked-out Git commit, then uploads `skill-catalog.tar.gz` and its `.sha256`
file. It requires Git, Bash, tar, and sha256sum; no Python, Node, site build,
policy evaluation, or assessment runs in this job. Untracked files are excluded.

From the repository root, build a committed candidate with:

```sh
bash scripts/package-skill-catalog.sh /tmp/catalog/skill-catalog.tar.gz
```

The existing release-workflow tests check exact folder membership, unchanged
supporting files, checksum integrity, untracked-file exclusion, and failure
before publication when a required skill is missing.

## Releases

`.github/workflows/release.yml` runs when a maintainer pushes a `v<version>` tag.
Tag creation is the release approval action: complete the human-reviewed checklist
in `docs/specs/release-process.md`, including clean GitLab Pages acceptance proof,
before tagging. This workflow does not create tags or approve release readiness.
The workflow publishes the prebuilt site plus the skill catalog download under
the same version. Publication still requires the existing site release checks;
the independent CI catalog download does not depend on the site build.

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

The GitHub Release contains the prebuilt `.tar.gz`, the shared
`release-manifest.json` and `SHA256SUMS.txt`, plus `skill-catalog-<version>.tar.gz`
and `skill-catalog-<version>.tar.gz.sha256`. The workflow packages the catalog
first, then passes `--catalog-archive` to the prebuilt builder. The shared manifest
lists both archives and the catalog checksum; `SHA256SUMS.txt` also covers the
manifest. The catalog retains its individual archive checksum. `gh release create --verify-tag`
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

## Dependency Vulnerability Management

GitHub Dependabot is the authoritative dependency-vulnerability control. Dependabot alerts and security updates must remain enabled in repository settings, and GitHub Security is the only alert backlog; do not create a scheduled CI job that duplicates it.

`.github/dependabot.yml` covers the root `pyproject.toml` and `uv.lock` with the `uv` ecosystem and `site/package.json` and `site/package-lock.json` with the `npm` ecosystem. Version updates run weekly on Monday. Minor and patch updates are grouped per ecosystem, while major updates remain separate. Dependabot uses its default dependency and ecosystem labels and assigns update pull requests to `Fnorgh2`.

`Fnorgh2` owns alert triage and must receive GitHub notifications for high- and critical-severity alerts. High and critical alerts are reviewed when received; the remaining backlog is reviewed weekly. Alerts that cannot be remediated promptly are escalated to repository administrator `scotluns`.

## GitHub Publication

The `SkillSpector` workflow publishes official evidence after default-branch skill changes, on its nightly schedule, and through manual dispatch. The publication job receives `contents: write`; other jobs remain read-only except for the review job's narrowly scoped `pull-requests: write` permission.

Publication commits only `.exchange/generated/boe/` and pushes it to the configured default branch. The job-scoped `GITHUB_TOKEN`, GitHub server URL, and repository path are mapped to the generic `EXCHANGE_PUBLISH_*` variables. Repository rules must permit this workflow to push generated-evidence commits.

Pull request comments use the job-scoped `GITHUB_TOKEN`. A scanner failure comment may include the native report's structured `metadata.llm_error`, but never captured scanner stdout or stderr; detailed failure output remains in the workflow logs and retained artifacts. When no structured LLM error is available, the comment says `SkillSpector failed. Check the CI logs for details.`

## Publish Authentication

The publication helper chooses push credentials in this order:

1. `EXCHANGE_PUBLISH_PUSH_URL`, when a complete authenticated remote URL is provided.
2. `EXCHANGE_PUBLISH_TOKEN`, `EXCHANGE_PUBLISH_USERNAME`, `EXCHANGE_PUBLISH_SERVER_URL`, and `EXCHANGE_PUBLISH_REPOSITORY` together.

No unrelated CI token is used as a fallback. Missing publication context fails closed.

## Configurable Variables

GitHub repository configuration uses Actions secrets and variables:

- `SKILL_EXCHANGE_LLM_API_KEY` is the LLM gateway secret.
- `SKILL_EXCHANGE_LLM_BASE_URL`, `SKILL_EXCHANGE_LLM_MODEL`, `SKILL_EXCHANGE_LLM_PROVIDER`, `SKILL_EXCHANGE_LLM_API_KEY_HEADER`, `SKILL_EXCHANGE_LLM_REQUESTS_PER_SECOND`, `SKILL_EXCHANGE_LLM_MAX_OUTPUT_TOKENS`, and `SKILL_EXCHANGE_SCAN_MAX_SECONDS` configure LLM-assisted scans.
- `RUNNER_CA_BUNDLE_PATH` identifies the readable enterprise CA bundle on each self-hosted SkillSpector runner.

The workflow maps GitHub context into these helper settings:

- `SKILL_EXCHANGE_REVIEW_SCAN_MODE`, `SKILL_EXCHANGE_REVIEW_FAIL_ON_VALIDATION_ERRORS`, `SKILL_EXCHANGE_REVIEW_FAIL_ON_SCANNER_ERROR`, and `SKILL_EXCHANGE_POST_REVIEW_COMMENT` control pull request review.
- `SKILL_EXCHANGE_PUBLISH_SCAN_MODES`, `EXCHANGE_PUBLISH_COMMIT`, `EXCHANGE_PUBLISH_PUSH`, and `EXCHANGE_PUBLISH_BRANCH` control official publication.
- `EXCHANGE_PUBLISH_PUSH_URL`, or the complete set of `EXCHANGE_PUBLISH_TOKEN`, `EXCHANGE_PUBLISH_USERNAME`, `EXCHANGE_PUBLISH_SERVER_URL`, and `EXCHANGE_PUBLISH_REPOSITORY`, configures authenticated BOE pushes.
- `EXCHANGE_BOT_GIT_NAME`, `EXCHANGE_BOT_GIT_EMAIL`, and `EXCHANGE_PUBLISH_COMMIT_MESSAGE` control generated commit metadata.

When the same skill content, SkillSpector version, scan mode, and scanner configuration have already produced BOE, scheduled publication should report reused scans and avoid committing new BOE. The first LLM-assisted publication for a cache key creates LLM-backed BOE; later runs with the same key should reuse it.
