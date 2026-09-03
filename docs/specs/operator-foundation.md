# Operator Foundation Spec

## Decision baseline

This spec follows `docs/decisions.md`: customers receive released artifacts from GitHub and operate them in GitLab; products remain independent and compose through contracts.

## Milestone

`docs/roadmap.md` section 3.7, Operator foundation.

## Status

Draft.

An agent must not execute this spec until a human reviewer changes this status
to Approved.

## Outcome

An operator installs compatible released components in GitLab, runs the reference pipeline, builds the site, and deploys it to GitLab Pages.

## Release artifact

GitHub Releases publish one archive named
`deployment-kit-operator-<version>.tar.gz`. After extraction, the archive root is
named `deployment-kit-operator-<version>/` and contains:

```text
deployment-kit-operator-<version>/
  .gitlab-ci.yml
  README.md
  compatible-versions.json
  release-manifest.json
  SHA256SUMS.txt
  .exchange/
    site-config.json
    display-policy.yaml
    categories.yaml
    tags.yaml
    risk-policy.yaml
  .gitlab/
    assessment-kit.gitlab-ci.yml
  ci/
    operator.gitlab-ci.yml
  contracts/
    skill-package/v1/
    boe/v1/
    assessment-artifacts/v1/
    release-manifest/v1/
  docs/
    install.md
    configure-gitlab.md
    build-and-deploy.md
    manual-boe-persistence.md
    troubleshooting.md
  vendor/
    assessment-kit/
      assessment-kit-<assessment-kit-version>.tar.gz
  scripts/
    operator/
      verify-inputs
      materialize-site-data
  site/
    package.json
    package-lock.json
    astro.config.mjs
    src/
```

Required release contents:

- `.gitlab-ci.yml` includes `ci/operator.gitlab-ci.yml` and the vendored
  `.gitlab/assessment-kit.gitlab-ci.yml` profile.
- `.gitlab/assessment-kit.gitlab-ci.yml` is copied unchanged from the compatible
  assessment-kit GitLab CI profile release so GitLab can resolve the local
  include before any job downloads artifacts.
- `ci/operator.gitlab-ci.yml` defines the operator input, site-data, site-build,
  and Pages jobs.
- `contracts/` contains the vendored schemas used by `verify-inputs` and
  `materialize-site-data`.
- `scripts/operator/verify-inputs` verifies customer-supplied release artifacts,
  checksums, manifests, and compatible versions.
- `scripts/operator/materialize-site-data` consumes the verified catalog,
  `.exchange/` site configuration, and verified BOE artifacts to produce static
  catalog data for the site build.
- `.exchange/` contains the default reference site policy and display
  configuration used by `materialize-site-data`.
- `site/` contains the reference site source and pinned build tooling.
- `docs/` explains installation, required GitLab variables, runner and assessor
  access, build outputs, deployment, manual BOE persistence, and
  troubleshooting.
- `vendor/assessment-kit/` contains the compatible assessment-kit release
  artifact used by the vendored assessment-kit CI profile.
- `release-manifest.json` conforms to the release-manifest v1 contract and
  records every file in the archive except itself and `SHA256SUMS.txt`.
- `SHA256SUMS.txt` contains SHA-256 entries for the same archive-relative paths
  recorded in `release-manifest.json`.

The initial catalog is test input, not a structural dependency.

## Compatible versions

`compatible-versions.json` is the operator release's compatibility declaration.
It is release metadata, not a new cross-product contract. It has this exact
shape:

```json
{
  "schema_version": "skill-exchange-operator-compatibility/v1",
  "operator_version": "<operator-version>",
  "products": {
    "skill-catalog": {
      "version": "<catalog-version>",
      "archive": "skill-catalog-<catalog-version>.tar.gz",
      "release_manifest_schema": "skill-exchange-release-manifest/v1",
      "required_contracts": {
        "skill-package": "v1",
        "release-manifest": "v1"
      },
      "optional_contracts": {
        "boe": "v1"
      }
    },
    "assessment-kit": {
      "version": "<assessment-kit-version>",
      "archive": "assessment-kit-<assessment-kit-version>.tar.gz",
      "release_manifest_schema": "skill-exchange-release-manifest/v1",
      "required_contracts": {
        "skill-package": "v1",
        "boe": "v1",
        "assessment-artifacts": "v1",
        "release-manifest": "v1"
      },
      "gitlab_ci_profile": ".gitlab/assessment-kit.gitlab-ci.yml"
    }
  }
}
```

The operator pipeline fails before advice, assessment, build, or deployment when
the downloaded catalog or assessment-kit release manifest reports a different
version, archive name, or release-manifest schema version than
`compatible-versions.json`. Required contract versions are compared against the
`required_contracts` and `optional_contracts` entries in
`compatible-versions.json`, not inferred from the release manifest. The operator
release must not accept unlisted major or minor versions by range.

## Contracts

The operator release consumes:

- Skill-package contract.
- BOE-manifest contract.
- Assessment-artifacts contract.
- Assessment-kit CLI contract.
- Release-manifest contract.

## Required GitLab variables

The reference CI fails closed when required variables are absent. Variable names
are generic and must not encode maintainer infrastructure, organization names,
or provider-specific service names.

| Variable | Description |
|---|---|
| `SKLC_CATALOG_URL` | URL for the compatible initial-catalog archive from GitHub Releases. |
| `SKLC_CATALOG_SHA256` | Expected SHA-256 digest for the catalog archive. |
| `SKLC_CATALOG_VERSION` | Exact catalog version from `compatible-versions.json`. |
| `SKLC_ASSESSMENT_KIT_PATH` | Local path set by `operator_prepare_inputs` for the compatible vendored assessment-kit artifact. |
| `SKLC_ASSESSMENT_KIT_SHA256` | Expected SHA-256 digest from `compatible-versions.json` for the vendored assessment-kit artifact. |
| `SKLC_ASSESSMENT_KIT_VERSION` | Exact assessment-kit version from `compatible-versions.json`. |
| `SKLC_ASSESSOR` | Supported assessor identifier consumed by the released assessment kit. |
| `SKLC_PREPARE_RUNNER_TAG` | GitLab runner tag for release download and verification. |
| `SKLC_ADVICE_RUNNER_TAG` | GitLab runner tag for the advice job from the assessment profile. |
| `SKLC_ASSESSMENT_RUNNER_TAG` | GitLab runner tag for the assessment job from the assessment profile. |
| `SKLC_BUILD_RUNNER_TAG` | GitLab runner tag for site-data materialization and site build. |
| `PAGES_RUNNER_TAG` | GitLab runner tag for the `pages` job. |

Required secret variables depend on the selected assessor and follow the
assessment-kit documentation. The operator docs must describe only generic
names, including `SKLC_LLM_API_KEY`,
`SKLC_LLM_BASE_URL`, `SKLC_LLM_MODEL`, and
`SKLC_LLM_PROVIDER` when the assessor requires model access. Secrets
are configured as masked GitLab CI/CD variables, protected when the customer's
branch model supports it. CI must not echo secrets, write secrets to artifacts,
accept secrets through committed files, or print the full environment.

The operator CI provides these assessment-profile variables with fixed values.
`operator_prepare_inputs` creates and verifies the corresponding paths before
the assessment jobs run:

| Variable | Value |
|---|---|
| `SKLC_SKILL_ROOT` | `.operator/inputs/catalog/skills` |
| `SKLC_ADVICE_OUTPUT_DIR` | `.operator/artifacts/advice` |
| `SKLC_ASSESSMENT_OUTPUT_DIR` | `.operator/artifacts/assessment` |

## CI sequence

The shipped CI declares these stages in order:

```yaml
stages:
  - operator_prepare
  - skill_advice
  - skill_assessment
  - site_data
  - site_build
  - deploy
```

The reference pipeline defines these jobs:

| Job | Stage | Inputs | Outputs |
|---|---|---|---|
| `operator_prepare_inputs` | `operator_prepare` | GitLab variables, `compatible-versions.json`, catalog URL, vendored assessment-kit artifact | Verified unpacked releases under `.operator/inputs/` |
| `assessment_kit_advise` | `skill_advice` | Prepared catalog skills and released assessment kit | `.operator/artifacts/advice/` |
| `assessment_kit_assess` | `skill_assessment` | Prepared catalog skills and released assessment kit | `.operator/artifacts/assessment/` including BOE with native reports and `verify-boe.log` |
| `operator_materialize_site_data` | `site_data` | Prepared catalog, site config, and verified assessment BOE | `.operator/generated/exchange/` and `.operator/generated/downloads/` |
| `operator_build_site` | `site_build` | `site/` source plus generated exchange data and downloads | `public/` |
| `pages` | `deploy` | `public/` from `operator_build_site` | Top-level GitLab Pages artifact `public` |

`operator_prepare_inputs` downloads the catalog archive, uses the compatible
assessment-kit artifact under `vendor/assessment-kit/`, verifies
`SKLC_*_SHA256`, unpacks them beneath `.operator/inputs/`, validates
their release manifests, and compares their versions, archive names,
release-manifest schema versions, and compatible contract entries to
`compatible-versions.json`. It fails before producing artifacts when any check
fails. It passes the prepared assessment-kit artifact to the vendored CI profile
through `SKLC_ASSESSMENT_KIT_PATH`.

Prepared input layout is canonical and strips the versioned archive root:

```text
.operator/inputs/
  catalog/
    README.md
    release-manifest.json
    SHA256SUMS.txt
    skills/
    boe/                 optional
    contracts/
  assessment-kit/
    README.md
    release-manifest.json
    SHA256SUMS.txt
    dist/
    contracts/
    docs/
```

For example, files from `skill-catalog-1.0.0/` are copied under
`.operator/inputs/catalog/`, and files from `assessment-kit-1.0.0/` are copied
under `.operator/inputs/assessment-kit/`. Downstream jobs must use these
canonical prepared paths and must not depend on versioned archive directory
names.

Every downstream job uses `needs` to consume only the artifacts it requires from
earlier jobs: assessment jobs need `operator_prepare_inputs`,
`operator_materialize_site_data` needs `operator_prepare_inputs` and
`assessment_kit_assess`, `operator_build_site` needs
`operator_materialize_site_data`, and `pages` needs `operator_build_site`.
Downstream jobs must not infer alternate locations when the configured paths are
missing.

`assessment_kit_advise` and `assessment_kit_assess` are the jobs from the
vendored assessment-kit GitLab CI profile. The operator CI must not change their
assessment-artifacts contract, must not allow advice to produce BOE, and must
not let the assessment job succeed unless `verify-boe` accepts the retained BOE.

`operator_materialize_site_data` is a Python or shell job, not a Node site-build
job. It validates every released catalog skill package and combines those skills
with the verified assessment BOE from `.operator/artifacts/assessment/boe/`. It
writes only derived build inputs under `.operator/generated/`. It does not
commit, push, call GitLab write APIs, or use runner caches as authoritative BOE.

`operator_build_site` runs the pinned site build from `site/` against the
generated exchange data. It must not download release inputs, evaluate catalog
policy, run assessment, or create BOE. Its successful output is exactly a
top-level `public/` directory containing `index.html`, `assets/`, and
`downloads/`.

`pages` is the GitLab Pages job. It must be named `pages`, use
`PAGES_RUNNER_TAG` for runner routing, and publish `public` through
`artifacts.paths` as the top-level Pages artifact.

## Operator script contracts

`scripts/operator/verify-inputs` is invoked only by
`operator_prepare_inputs`:

```text
scripts/operator/verify-inputs \
  --catalog-archive <path> \
  --catalog-sha256 <sha256> \
  --assessment-kit-archive <path> \
  --assessment-kit-sha256 <sha256> \
  --compatible-versions compatible-versions.json \
  --output .operator/inputs
```

It validates checksums, rejects archive paths that extract outside the output
directory, rejects escaping symbolic links, validates both release manifests
against the vendored release-manifest schema, compares exact versions and
archive names to `compatible-versions.json`, confirms required contract
directories exist in the extracted releases, and writes only under
`.operator/inputs/`. Exit `0` means all inputs were verified and prepared; exit
`2` means invalid input, checksum mismatch, schema failure, incompatible version,
missing contract, unsafe path, or filesystem failure.

`scripts/operator/materialize-site-data` is invoked only by
`operator_materialize_site_data`:

```text
scripts/operator/materialize-site-data \
  --catalog-root .operator/inputs/catalog \
  --assessment-boe-root .operator/artifacts/assessment/boe \
  --config-root .exchange \
  --site-root site \
  --output .operator/generated
```

It validates released skill packages, effective BOE, display
configuration, generated path safety, and downloadable skill artifacts. It
writes only under `.operator/generated/`. Exit `0` means generated site data and
downloads are complete; exit `2` means invalid released skill, duplicate skill
name, invalid BOE, missing required artifact, unsafe path, invalid
configuration, or filesystem failure. Neither script may call Git, GitLab APIs,
assessment commands, or the site build.

## Build inputs and outputs

`scripts/operator/materialize-site-data` consumes these minimal configuration
shapes:

`.exchange/site-config.json`:

```json
{
  "title": "Skill Exchange",
  "base_path": "/",
  "downloads_path": "downloads"
}
```

`.exchange/display-policy.yaml`:

```yaml
show_boe: true
default_sort: name
```

`.exchange/categories.yaml`:

```yaml
categories:
  - id: security
    label: Security
```

`.exchange/tags.yaml`:

```yaml
tags:
  - security
```

`.exchange/risk-policy.yaml`:

```yaml
risk_levels:
  low: []
  medium: []
  high: []
```

The materializer validates every skill discovered under
`.operator/inputs/catalog/skills/` and publishes every valid released catalog
skill. Duplicate skill names, invalid released skills, invalid effective BOE, or
paths outside the prepared input tree fail the job before site data is written.
Missing BOE does not change publication.

The site-data materialization input tree is:

```text
.operator/inputs/catalog/
  skills/
  boe/                 optional input from the catalog release
.operator/artifacts/assessment/
  boe/
  verify-boe.log
.exchange/
site/
```

The assessment-produced BOE is the BOE used for the operator proof. Optional BOE
from the catalog release may be used only when the assessment job selected no
skills; otherwise the build fails if an assessed published skill has no verified
assessment BOE.

The materialization output tree is:

```text
.operator/generated/
  exchange/
    skills.json
    skill-details/
    scanner-runs/
  downloads/
    skills/
  build-input-manifest.json
```

`build-input-manifest.json` records the catalog version, assessment-kit version,
operator version, published skill names, and the digests of BOE manifests used
for the build. It records relative paths only.

`skills.json` is an array of selected skills with this minimum shape:

```json
[
  {
    "name": "python-secure-code-review",
    "title": "Python Secure Code Review",
    "description": "Review Python code for security issues.",
    "detail_path": "skill-details/python-secure-code-review.json",
    "download_path": "downloads/skills/python-secure-code-review.zip",
    "boe_path": "scanner-runs/python-secure-code-review.json"
  }
]
```

`skill-details/<skill-name>.json` contains the selected skill's frontmatter,
renderable content, release source path, download path, and optional BOE path.
`scanner-runs/<skill-name>.json` contains the verified BOE path and report
digests used for that skill. All generated paths are relative to
`.operator/generated/exchange/` or `.operator/generated/downloads/` and must not
contain parent-directory traversal.

The site-build output tree is:

```text
public/
  index.html
  assets/
  downloads/
```

`public/downloads/` contains every downloadable skill artifact referenced by the
generated site data. The build fails when `public/index.html` is missing, a
referenced download is absent, or generated data references a path outside
`public/`.

## BOE artifacts and manual persistence

The operator pipeline retains advice and assessment artifacts with
`when: always`, but success still depends on non-zero command handling and
post-run verification. The assessment artifact contains:

```text
.operator/artifacts/assessment/
  boe/
  verify-boe.log
```

Manual BOE persistence is documentation-only in this milestone. The CI makes no
source-control changes by default and must not run `git add`, `git commit`,
`git push`, GitLab write APIs, or equivalent persistence steps.

`docs/manual-boe-persistence.md` must instruct an operator to:

1. Download the successful `assessment_kit_assess` job artifact.
2. Review the native reports referenced from
   `.operator/artifacts/assessment/boe/` and the verification log.
3. Copy accepted BOE files and their referenced native reports from
   `.operator/artifacts/assessment/boe/` into the target catalog source tree using the
   initial-catalog BOE layout:

```text
boe/
  <skill-name>/
    boe.json
    assessments/
```

4. Re-run the released assessment kit's `verify-boe` command against each copied
   skill and BOE directory.
5. Commit the accepted BOE using the customer's normal source-control process.

These steps prepare BOE for a later catalog release or customer source-control
process. They do not add operator overlay, update, or bot-persistence support to
this milestone.

## GitLab proof

Acceptance requires a clean GitLab project that:

1. Receives `deployment-kit-operator-<version>.tar.gz` from GitHub Releases and
   commits the extracted operator files unchanged.
2. Configures the required GitLab variables for the compatible catalog,
   assessment kit, runners, credentials, and assessor access.
3. Runs `operator_prepare_inputs` and verifies catalog and assessment-kit
   checksums, release manifests, exact versions, archive names, and compatible
   contract entries.
4. Runs advice without producing BOE.
5. Runs formal assessment, retains native reports and BOE, and succeeds only
   after `verify-boe` accepts the retained BOE.
6. Materializes site data from the released skill packages and verified BOE.
7. Builds `public/` from the reference site source.
8. Publishes a GitLab Pages artifact from a job named `pages`.

Acceptance evidence must include the GitHub Release tag and filenames used, the
configured compatible product versions, and a GitLab pipeline URL or job log
excerpt showing `operator_prepare_inputs`, `assessment_kit_advise`,
`assessment_kit_assess`, `operator_materialize_site_data`,
`operator_build_site`, and `pages` passed.

## Exclusions

- Operator-owned `local/` overlay.
- Preservation of operator changes across updates.
- Automatic source-control changes by default.
- Generic static-host validation.
- Partial or full update support.
- Bot-driven BOE persistence.
