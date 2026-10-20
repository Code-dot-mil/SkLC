# Operator kit

Assess a skill catalog and publish its exchange with the supplied GitLab pipeline.
The kit includes reference skills, the assessment wheel, an assessment-image
Dockerfile, and the site sources. Start here after extracting the operator ZIP.

## Before you start

You need Git, Docker with BuildKit to build the assessment image, and permission
to create and push to a GitLab project and configure its CI/CD variables.
The site build needs Node.js 22.22.0 or later; CI supplies it through `NODE_IMAGE`.

Confirm that the project has access to a trusted Linux runner that supports
container job images. Ask its administrator for the runner tag and architecture
if necessary. A runner executes the job; the image supplies its software. See
[runner availability](https://docs.gitlab.com/ci/runners/runners_scope/) and
[container jobs](https://docs.gitlab.com/ci/docker/using_docker_images/).
Assessment needs registry/package access and access to the selected model
provider. The build job needs access to npm packages.

Choose a registry where you can publish the assessment image and from which the
runner can pull it. Workstation registry login does not configure runner access.
For a private registry, configure
[image pull credentials](https://docs.gitlab.com/ci/docker/using_docker_images/#access-an-image-from-a-private-container-registry)
before starting a job; login in its script happens too late to pull its own image.

## Install into an empty project

Download `deployment-kit-operator-<version>.zip` from
[SkLC releases](https://github.com/Code-dot-mil/SkLC/releases). Compare its SHA-256
with GitHub's asset digest, then extract it into its own directory. A ZIP from
a PR's CI check is an experimental preview, not a published release; retain its
run, commit, and checksum when evaluating it.

[Create a blank GitLab project](https://docs.gitlab.com/user/project/) in the
intended group. Leave **Initialize repository with a README** unchecked. Use a
new empty project rather than copying the kit over an existing repository.
Copy the clone URL from **Code**. From the extracted kit directory, replace the
angle-bracket values and run:

```sh
git clone "<gitlab-project-url>" "../<project-directory>"
cp -a . "../<project-directory>/"
cd "../<project-directory>"
git add -A
git commit -m "feat: install operator kit"
git branch -M "<default-branch>"
git push -u origin "<default-branch>"
```

The destination must be outside the extracted directory. Confirm that
`.gitlab-ci.yml` and `.exchange/` were copied. Use the default branch selected for
the project, which may be named `main`.

Retain, extend, or replace the reference catalog under `skills/ai4sdlc/`.
Place packages in `skills/<namespace>/<skill>/`, including supporting files and a
`SKILL.md` with a matching name and nonempty description. Configure categories,
tags, and display settings through `.exchange/`. Commit catalog changes before
running the pipeline so source links identify the assessed revision.

## Build and publish the assessment image

Follow the [assessment image guide](../../containers/assessment/README.md) to
build for the runner's architecture, verify the scanner, publish the image, and
record its digest. The supplied image runs as a nonroot user and allows the job
to install the packaged wheel. The runner must make its checkout writable to
that user.

The image guide also covers optional private CA certificates. Build-time trust
does not configure runtime provider trust. Keep verification enabled and obtain
extra CA certificates from a trusted administrator or authenticated PKI source.
When configured, the packaged helper combines those certificates with the
image's public roots before installing the wheel and running assessment. Keep these extra CA files
out of the repository, image layers, and published artifacts.

## Configure GitLab

Open **Settings > CI/CD > Variables** and add the required settings below.
Each runner-tag variable holds one tag; the same tag can serve multiple jobs
when that runner meets their requirements. GitLab explains
[tag matching](https://docs.gitlab.com/ci/runners/configure_runners/#how-the-runner-uses-tags).

| Variable | Purpose and default |
| --- | --- |
| `ASSESSMENT_IMAGE` | Required: full published image reference, preferably pinned by digest; use the supplied Dockerfile or an image with Python 3.12+, pip, Git, and SkillSpector `>=2.10,<3` on PATH (2.10.0 tested) |
| `ASSESSMENT_RUNNER_TAG` | Required: trusted container runner with assessor/provider access |
| `BUILD_RUNNER_TAG` | Required: container runner able to install npm dependencies |
| `PAGES_RUNNER_TAG` | Required: container runner for the Pages job |
| `SCAN_MODE` | `llm-assisted` (default) or explicitly `static-only` |
| `NODE_IMAGE` | Defaults to `node:22`; replacement must provide Node >=22.22.0 and npm |
| `PAGES_IMAGE` | Defaults to `alpine:3.24.2`; replace for your registry if needed |
| `ASSESSMENT_CA_CERTIFICATES` | Optional **File** variable containing only verified extra public CA certificates in PEM format; see the image guide |

For LLM-assisted assessment, configure the provider, model, and credentials from
the [assessment provider guide](../../../assessment-kit/README.md#adjudication-gateways).
Skill contents are sent to that provider. Store credentials as masked variables
(masked and hidden where supported), disable variable expansion, and protect
them. Confirm that the default branch is
[protected](https://docs.gitlab.com/user/project/repository/branches/protected/)
so it receives protected variables. Use environment scope `*` for these jobs.
See [project variables](https://docs.gitlab.com/ci/variables/#for-a-project).
Do not enter credentials in source files or the New pipeline form.

To omit model requests, set `SCAN_MODE=static-only`. **This is not recommended**
due to a consistently high rate of false positives that require manual review.
Failed LLM-assisted assessment never switches to static-only. Package downloads
and scanner network lookups may still need network access in either mode.

Under **Settings > General > Visibility, project features, permissions**, enable
Pages and select the intended audience. Check the Pages setting even for a
private repository; see
[Pages access control](https://docs.gitlab.com/user/project/pages/pages_access_control/).

## Run and verify

Open **Build > Pipelines > New pipeline**, select the default branch, and start
the run. The supplied workflow accepts only this web action on the default
branch. Pushes, schedules, merge requests, and API triggers do not start it.
See [GitLab's manual pipeline guide](https://docs.gitlab.com/ci/pipelines/#run-a-pipeline-manually).

The flow is **Assess → Generate → Build → Pages**. Assess scans each skill once
and records its adjudication. Findings, completed negative judgments, and
nonfatal coverage gaps remain advisory evidence and allow publication. Scanner
execution, requested inference, adjudication, or evidence-writing failures stop
dependent jobs. The failed assessment job still attempts to upload available
diagnostics; runner interruption or timeout can prevent upload.

Generation reads current `skillspector.json` and `adjudication.json` from
`evidence/<namespace>/<skill>/` without rescanning or verifying package hashes. Keep assessments with their matching source content.
After success, open **Deploy > Pages** and use the displayed URL. Check the styled
catalog, a skill page, its package ZIP, source revision link, and native scanner
report download. See [GitLab Pages](https://docs.gitlab.com/user/project/pages/).

| Location | Available evidence |
| --- | --- |
| Assessment job's `evidence/` artifact | Current raw `skillspector.json`, `adjudication.json`, `scanner.log`, and action-based `assessment.md`; failed runs retain whichever diagnostic files could be written |
| Generate job's `.exchange/generated/` artifact | Catalog data, skill ZIPs, and per-run `skillspector.json`, scanner-derived `summary.json`, and an adjudication copy named `boe.json` |
| Published site and `public/` artifact | Skill packages and those three per-run JSON downloads; the page displays scanner findings/risk and links the native report |

To retrieve the scanner-derived summary or adjudication copy from the site, replace
`skillspector.json` in the native-report download URL with `summary.json` or
`boe.json`. The adjudication copy is not a complete downloadable assessment bundle.

The site publishes the adjudication copy but does not publish scanner logs.
The generated summary describes scanner risk; it is not an adjudication
or a separate LLM-written summary. Use the adjudication for its scope and coverage
judgment, and the raw scanner report to inspect individual model calls.

## Retain evidence and run again

Download the archive from the specific assessment job or **Build > Artifacts**.
The template requests 30-day expiry; GitLab retention settings can keep current
artifacts longer. A latest-artifacts link can change after another run. See
[job artifacts](https://docs.gitlab.com/ci/jobs/job_artifacts/).

For durable history, retain each skill's `skillspector.json` and
`adjudication.json` together with their matching catalog revision. These two files
are the BOE; review and commit that pair when keeping evidence in the checkout.
Keep `scanner.log` in diagnostic artifacts only. The pipeline makes no commits or pushes.

Every pipeline run reassesses skills and replaces the three current report files
only after successful scanning and adjudication. This incurs provider usage in
LLM-assisted mode. Failed runs retain diagnostics separately and preserve current
reports. Download or commit evidence before rerunning to retain earlier results.
Use `--if-changed` locally to reuse valid reports for unchanged content and mode.
See [current assessments](../../../assessment-kit/README.md#assess).

## Run locally

Activate a Python 3.12+ environment with SkillSpector and Git on PATH, following
the [assessment prerequisites](../../../assessment-kit/README.md#prerequisites).
Use Node.js 22.22.0 or later. Run from the installed kit root:

```sh
python -m pip install wheels/*.whl
export PYTHONPATH=scripts
export SKILL_EXCHANGE_SOURCE_REPOSITORY_URL="<gitlab-project-url>"
export SKILL_EXCHANGE_SOURCE_BRANCH="$(git rev-parse HEAD)"
python -m skill_exchange.operator assess --scan-mode static-only
python -m skill_exchange.operator generate --scan-mode static-only
npm ci --prefix site
npm --prefix site run build
```

For LLM-assisted assessment, configure the provider and use `--scan-mode
llm-assisted` in both commands. For private CA trust, follow the image guide's
local helper instructions before the wheel installation. Each assessment also
writes `assessment.md` with required remediation, unresolved findings, and false
positives from the current reports.

Paths are configurable with `--skills`, `--evidence`, `--policy`, and `--generated`.
For a custom generated path, set `SKILL_EXCHANGE_GENERATED_ROOT` to the same
absolute path for Node. Local output is in `site/dist/`.

## Troubleshooting

A pending job usually needs an available runner with matching tags. An image-pull
failure needs registry access before the job can start. Missing credentials need
a check of variable protection and scope. Certificate errors need runtime trust
inside the job image, even when the same request works on your workstation.
For inference failures, inspect provider availability and the retained reports.
See [GitLab pipeline debugging](https://docs.gitlab.com/ci/debugging/) and the
[assessment guide](../../../assessment-kit/README.md) for report interpretation.
