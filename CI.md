# Skill Exchange CI

The repository owns GitHub validation in `.github/workflows/ci.yml` and release publication in `.github/workflows/release.yml`.

## GitHub Validation

The `CI` workflow runs on every pull request targeting `main` and every push to `main`. GitHub-hosted Ubuntu runners execute the Python and site lint and test commands defined by the local `Justfile`; any failed command blocks the final artifact job. A Python producer checks out full history, reads successful exact-current-content tracked BOE. Missing or invalid evidence fails the build; CI does not run a scanner or create replacement evidence. Repository and immutable commit context from the pull-request head or push override the placeholder site configuration so generated source links target the revision being built, including for fork pull requests. The Node.js consumer downloads the generated data and builds `site/dist/`.

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
in `.agents/skills/sklc-release-process/SKILL.md`, including clean GitLab Pages acceptance proof,
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
