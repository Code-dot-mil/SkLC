# Operator kit

Assess a skill catalog and publish its exchange with the supplied GitLab pipeline.
The kit includes upstream skills and assessments, the assessment
wheel, an assessment-image Dockerfile, and the site sources. Start here after extracting the operator ZIP.

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
`.gitlab-ci.yml`, `src/`, and `assessment/` were copied. Use the default branch selected for
the project, which may be named `main`.

Create your local catalog directories:

```sh
mkdir -p skills evidence
```

Place your own complete packages in `skills/<skill>/`, with matching
`name` and nonempty `description` in `SKILL.md`. To serve upstream developer
skills, copy all, some, or none from `upstream/skills/`. Copy each selected
skill's matching JSON pair from `upstream/evidence/<skill>/` at the same time.
For example, to include the secure code review skill:

```sh
cp -R upstream/skills/python-secure-code-review skills/
cp -R upstream/evidence/python-secure-code-review evidence/
```

The `upstream/` directory contains included skills and assessments; generation reads
only `skills/` and `evidence/`. Review existing same-named local packages before
copying upstream packages again. Commit your catalog and matching evidence together.

## Build and publish the assessment image

Follow the [assessment image guide](../containers/assessment/README.md) to
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
| `SCAN_MODE` | `llm-assisted` (default) requests model assessment; `static-only` omits model requests |
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

Static-only assessment is available locally for diagnostics and retains unresolved
findings and limitations in the shared summary. Publishing requires a completed
LLM-assisted pair; setting `SCAN_MODE=static-only` in this pipeline stops generation.
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

The flow is **Assess → Generate → Build → Pages**. Assess reuses current reports
and scans changed skills, recording adjudication. Use `assess-catalog --force` to
reassess every skill. Findings, completed negative judgments, and
nonfatal coverage gaps remain advisory evidence and allow publication. Scanner
execution, requested inference, adjudication, or evidence-writing failures stop
dependent jobs. The failed assessment job still attempts to upload available
diagnostics; runner interruption or timeout can prevent upload.

Generation reads current `skillspector.json` and `adjudication.json` from
`evidence/<skill>/`, verifies the shared package hash, and preserves the paired assessment
status and its limitations. Keep assessments with
their matching source content. Generation runs no scanner and writes no evidence.
After success, open **Deploy > Pages** and use the displayed URL. Check the styled
catalog, a skill page, its package ZIP, and two JSON report downloads. See [GitLab Pages](https://docs.gitlab.com/user/project/pages/).

The site shows adjudication guidance, its exact summary, status, coverage judgment,
disposition counts, and limitations, alongside the original scanner display.
Consumers can download `skillspector.json` and `adjudication.json`. Scanner logs
remain job diagnostics. The assessment job retains the CLI action summary in
`assessment.md` for review without opening the site.

## Retain evidence and run again

Download the archive from the specific assessment job or **Build > Artifacts**.
The template requests 30-day expiry; GitLab retention settings can keep current
artifacts longer. A latest-artifacts link can change after another run. See
[job artifacts](https://docs.gitlab.com/ci/jobs/job_artifacts/).

For durable history, extract the archive's `evidence/` directory into the catalog
checkout, review it, and commit it with its matching catalog revision. Keep each JSON pair with its matching skill content. The pipeline makes no commits or pushes.

Pipeline and local assessment runs reuse valid current reports by default and
scan skills whose content or requested mode has changed. Use
`assess-catalog --force` to reassess all skills. Scanning in LLM-assisted mode
incurs provider usage and replaces current reports only after successful scanning
and adjudication. Failed runs retain diagnostics separately and preserve current
reports. Download or commit evidence before rerunning to retain earlier results.
See [current assessments](../../../assessment-kit/README.md#assess).

## Run locally

Activate a Python 3.12+ environment with SkillSpector and Git on PATH, following
the [assessment prerequisites](../../../assessment-kit/README.md#prerequisites).
Use Node.js 22.22.0 or later. Run from the installed kit root:

```sh
python -m pip install --upgrade --force-reinstall . -r assessment/requirements.txt
python -m skill_exchange.cli assess-catalog --scan-mode llm-assisted
python -m skill_exchange.cli generate
npm ci --prefix site
SKILL_EXCHANGE_GENERATED_ROOT="$PWD/.exchange/generated" npm --prefix site run build
```

Configure the provider before requesting `llm-assisted` assessment. Use
`--scan-mode static-only` for local diagnostics and summarize those reports;
these reports are not eligible for site generation. For private CA trust, follow the image guide's
local helper instructions before the wheel installation. Each assessment also
writes `assessment.md` by summarizing its existing reports without another scan.

Paths are configurable with `--skills`, `--evidence`, and `--generated`.
For a custom generated path, set `SKILL_EXCHANGE_GENERATED_ROOT` to the same
absolute path for Node. Local output is in `site/dist/`.

## Apply an update

Review and commit your instance before updating. Verify the new ZIP digest as
for installation. From the installed kit root, replace upstream-owned component
directories before extraction so files removed by upstream disappear too:

```sh
rm -rf -- build site src assessment ci upstream
unzip -o deployment-kit-operator-<version>.zip -d .
python -m pip install --upgrade --force-reinstall . -r assessment/requirements.txt
```

The disposable `build/` directory can retain removed Python modules from earlier
installs. Remove it when replacing the upstream runtime so those modules cannot
return in the installed package.

The archive and replacement list contain no live `skills/` or `evidence/` paths.
Updated upstream skills and their paired reports appear only in `upstream/`;
decide explicitly whether to copy any into the live catalog. The requirement file
selects the exact bundled wheel. Regenerate and rebuild after updating.

Supported customization is your skill catalog and its assessments. If you replace
another component, you own that entire component. Omit its paths from the removal
command **and** exclude them from extraction on every update. For a customized UI:

```sh
rm -rf -- build src assessment ci upstream
unzip -o deployment-kit-operator-<version>.zip -d . -x 'site/*'
python -m pip install --upgrade --force-reinstall . -r assessment/requirements.txt
```

Use the complete ownership boundary for each component:

| Component | Omit from replacement | Exclude from extraction |
| --- | --- | --- |
| Site UI | `site` | `site/*` |
| Customer CI | `ci`, `.gitlab-ci.yml` | `ci/*`, `.gitlab-ci.yml` |
| Assessment tooling and its CI | `assessment`, `ci`, `.gitlab-ci.yml` | `assessment/*`, `ci/*`, `.gitlab-ci.yml` |
| Deployment runtime | `build`, `src`, `pyproject.toml` | `src/*`, `pyproject.toml` |

Root files such as `.gitlab-ci.yml` and `pyproject.toml` are replaced by extraction;
exclude them with their component. Combine all applicable exclusions in one unzip
command. Use the installation procedure owned by your customized assessment or
runtime component when those components are excluded. You are responsible for
compatibility and incorporating desired upstream changes into components you own;
we do not merge incremental customizations.

## Troubleshooting

A pending job usually needs an available runner with matching tags. An image-pull
failure needs registry access before the job can start. Missing credentials need
a check of variable protection and scope. Certificate errors need runtime trust
inside the job image, even when the same request works on your workstation.
For inference failures, inspect provider availability and the retained reports.
See [GitLab pipeline debugging](https://docs.gitlab.com/ci/debugging/) and the
[assessment guide](../../../assessment-kit/README.md) for report interpretation.
