# Deployment Kit Prebuilt Spec

## Decision baseline

This spec follows `docs/decisions.md`: GitHub is the maintainer source of truth and release origin; GitLab is the customer deployment environment; products remain standalone.

## Milestone

`docs/roadmap.md` section 3.1, MVP - Prebuilt reference site.

## Status

Approved.

## Outcome

A customer downloads one GitHub Release artifact, verifies it, installs it unchanged, and deploys it to GitLab Pages or another static hosting service.

## Release artifact

The GitHub Release attaches one install archive named `deployment-kit-prebuilt-<version>.tar.gz`.
After extraction, the archive root is named `deployment-kit-prebuilt-<version>/` and contains exactly the deployable customer package:

```text
deployment-kit-prebuilt-<version>/
  .gitlab-ci.yml
  README.md
  docs/
    install.md
    deploy-gitlab-pages.md
    deploy-static-hosting.md
  contracts/
    release-manifest/v1/
      release-manifest.schema.json
  scripts/
    verify_prebuilt.py
  public/
    index.html
    assets/
    downloads/
  release-manifest.json
  SHA256SUMS.txt
```

Required release contents:

- `public/` contains the final static site output. It must be deployable as-is and must include `index.html`.
- `public/downloads/` contains every downloadable skill artifact referenced by the prebuilt site. Each referenced download path must exist in the archive.
- `.gitlab-ci.yml` is deployment-only GitLab CI. It must not build the site, assemble a catalog, run assessment tooling, or fetch release inputs.
- `README.md` is the entry point and links to `docs/install.md`, `docs/deploy-gitlab-pages.md`, and `docs/deploy-static-hosting.md`.
- `docs/install.md` documents extraction, checksum verification, and how to prepare the extracted files for the selected hosting path.
- `docs/deploy-gitlab-pages.md` documents the required GitLab project, local Git, runner, push, pipeline, Pages, and expected successful job behavior.
- `docs/deploy-static-hosting.md` documents how to host the released `public/` directory on a static web server or static hosting service.
- `release-manifest.json` conforms to `contracts/release-manifest/v1/release-manifest.schema.json`.
- `contracts/release-manifest/v1/release-manifest.schema.json` is vendored so customer verification does not require network access.
- `scripts/verify_prebuilt.py` is the single offline verifier used by installation and GitLab CI. It requires Python 3.12 or newer and no third-party packages.
- `SHA256SUMS.txt` contains checksums for the same archive-relative paths recorded in `release-manifest.json`.

The `assets/` and `downloads/` directories may contain nested files. This spec requires their deployable location and verification behavior only; it does not specify site internals, page layout, visual content, or skill presentation details beyond static output that can be served by GitLab Pages or another static host.

## Manifest and checksums

`release-manifest.json` requirements:

- `schema_version` is `skill-exchange-release-manifest/v1`.
- `version` exactly matches `<version>` in the archive filename and root directory.
- `artifacts` records every file required for customer installation except `release-manifest.json` and `SHA256SUMS.txt`.
- Each `artifacts[].path` is relative to the archive root, does not start with `/`, and does not contain `..`.
- Each `artifacts[].sha256` uses the schema format `sha256:<64 lowercase hex characters>`.
- At minimum, the manifest records `.gitlab-ci.yml`, `README.md`, every required file under `docs/`, `contracts/release-manifest/v1/release-manifest.schema.json`, `public/index.html`, and every file under `public/assets/` and `public/downloads/`.

`SHA256SUMS.txt` requirements:

- Each line uses the conventional format `<64 lowercase hex characters>  <archive-relative path>`.
- The file set and digest values must match `release-manifest.json` after removing the `sha256:` prefix from manifest digests.
- Verification fails if any recorded file is missing, any digest differs, any extra file is referenced by the site but absent from `public/downloads/`, or any path escapes the archive root.

The install documentation must give a copy/paste verification flow that validates both files: schema validation for `release-manifest.json`, digest verification from `SHA256SUMS.txt`, and a manifest-to-checksum comparison.

Both installation and the shipped GitLab job run
`python3 -I -S scripts/verify_prebuilt.py .` from the package/project root.
The verifier must reject unsupported schema features instead of silently skipping
them. It checks timestamp syntax, calendar dates, and timezone offset ranges;
space-separated dates and invalid offsets such as `+01:60` must fail.
Its manifest file set must match the installation files on disk, including the
verifier itself. Only the two root metadata files and the customer's top-level
`.git` entry are excluded from that comparison. Package links and unsafe paths
must fail. Installation additionally passes `--expected-version` to compare the
manifest with the selected archive version. The default verification must work
in a GitLab checkout with an arbitrary directory name.

## Guided documentation requirements

The released documentation must guide installation from setup through
deployment. It must identify each prerequisite decision, explain why the step
matters, and point to the exact official documentation page for deeper
platform-specific instructions.

The README and install docs must start by asking the customer to choose one
hosting path:

- GitLab Pages, using the shipped `.gitlab-ci.yml`.
- Another static hosting service or web server, using the released `public/`
  directory.

The GitLab Pages path must cover these prerequisites and link to the official
docs at the point where the customer may need them:

- A GitLab project for the site, with a link to
  `https://docs.gitlab.com/user/project/`.
- GitLab Pages, with a link to `https://docs.gitlab.com/user/project/pages/`.
- Local Git installed and configured with a commit name and email, with links to
  `https://git-scm.com/book/en/v2/Getting-Started-First-Time-Git-Setup` and
  `https://git-scm.com/docs/user-manual`.
- Permission to push to the target repository.
- At least one GitLab runner that can run the shipped `pages` job. The docs must
  explain that runners execute CI jobs, that runner tags control which jobs a
  runner can pick up, and that customers may need to ask their GitLab
  administrator which runner tags are available. Link to
  `https://docs.gitlab.com/ci/runners/`,
  `https://docs.gitlab.com/ci/runners/runners_scope/`, and
  `https://docs.gitlab.com/user/get_started/get_started_runner/`.
- Project or group CI/CD variables when `PAGES_RUNNER_TAG` is needed, with a link
  to `https://docs.gitlab.com/ci/variables/`.
  The docs must direct customers to the GitLab project UI locations for runner
  and variable settings, including `Settings > CI/CD > Runners` and
  `Settings > CI/CD > Variables`.

`docs/deploy-gitlab-pages.md` must include a concise path for:

1. Creating or selecting an empty GitLab project.
2. Confirming Git is configured locally.
3. Adding the extracted release files to the repository.
4. Committing and pushing the files.
5. Confirming the pipeline uses an available runner.
6. Finding the Pages deployment result.

`docs/deploy-static-hosting.md` must explain that the released `public/`
directory is the static site root. It must include concise examples or pointers
for common static hosting paths, including:

- A generic static web server that serves `public/index.html`.
- Apache HTTP Server, linking to
  `https://httpd.apache.org/docs/current/en/getting-started.html`.
- NGINX, linking to `https://nginx.org/en/docs/beginners_guide.html`.
- Google Cloud static website hosting, linking to
  `https://docs.cloud.google.com/storage/docs/hosting-static-website`.

Command examples must be safe to copy and paste:

- Commands that can run unchanged must not contain placeholder tokens.
- Commands that require customer-specific values must first list every value to
  replace, what it means, and where to find it.
- Placeholder values must use an obvious marker such as `<gitlab-project-url>`.
  A command containing such a marker must be labeled as a template, not as a
  command to run unchanged.
- If a copy/paste command uses shell variables, the docs must show the variable
  assignments immediately before the command and explain which values must be
  edited before running it.
- Commands must not depend on unstated working directories, hidden files, prior
  aliases, or local machine paths.

## Download reference rule

The prebuilt site may reference downloadable skill artifacts only through
relative URLs whose normalized path starts with `downloads/`. The release
verification script must scan `public/**/*.html`, `public/**/*.json`, and
`public/**/*.js` for static `href`, `src`, and JSON string values beginning
with `downloads/`. Each discovered path must resolve beneath
`public/downloads/`, must not contain `..`, and must exist as a regular file in
the archive. Query strings and fragments are ignored for file lookup. Dynamic
runtime construction of download URLs is out of scope for this milestone.

## GitLab Pages CI contract

The shipped `.gitlab-ci.yml` must define a job named `pages`. The job contract is:

- Input: tracked files from the extracted archive committed into a clean GitLab project.
- Required output: a top-level `public/` artifact published by GitLab Pages.
- Stage: any documented stage is acceptable, but the job must run without maintainer-only release jobs or external CI imports.
- Script behavior: verify `release-manifest.json` and `SHA256SUMS.txt`, then leave the existing `public/` directory as the Pages artifact.
- Artifact behavior: publish `public/` through `artifacts.paths` with `public` as the top-level path.
- Runner routing: if runner tags are needed, they must be configurable through `PAGES_RUNNER_TAG`; the CI must not hardcode organization-specific runner tags.
- Network behavior: the job must not download dependencies, fetch catalog artifacts, run a static-site generator, or call assessment tools.

The job succeeds only when all verification checks pass and GitLab accepts `public/` as the Pages artifact. It fails closed before publishing when required files are missing, checksums do not match, the manifest is invalid, `public/index.html` is absent, or referenced downloads are absent.

## Install verification

The documented customer verification path is:

1. Download `deployment-kit-prebuilt-<version>.tar.gz` from GitHub Releases.
2. Extract the archive.
3. Confirm the extracted root directory name matches the archive version.
4. Validate `release-manifest.json` against `contracts/release-manifest/v1/release-manifest.schema.json`.
5. Verify every digest in `SHA256SUMS.txt`.
6. Compare `release-manifest.json` artifact entries to `SHA256SUMS.txt`.
7. Commit the extracted files unchanged to a clean GitLab project.
8. Run the GitLab pipeline and confirm the `pages` job publishes the unchanged `public/` artifact.

No customer-side build, assessment execution, catalog assembly, or operator customization is part of installation verification. The milestone acceptance proof remains GitLab Pages; the documentation also covers static hosting alternatives.

## Contracts

The release produces a release manifest. It consumes no assessment, catalog, operator overlay, or build contracts at customer install time.

## GitLab proof

Acceptance requires a clean GitLab project that:

1. Receives the artifact from GitHub Releases.
2. Verifies the checksums.
3. Uses the shipped `.gitlab-ci.yml`.
4. Runs a `pages` job that verifies the manifest and checksums.
5. Publishes the unchanged `public/` content to GitLab Pages.

Acceptance evidence must include the GitLab pipeline URL or job log excerpt showing the `pages` job passed and the Pages deployment served `public/index.html`. It must also identify the GitHub Release tag and archive filename used for installation.

## Exclusions

- Customer-side site build.
- Assessment tooling or execution.
- Catalog assembly.
- Operator customization.
- Acceptance validation for every static hosting option documented.
