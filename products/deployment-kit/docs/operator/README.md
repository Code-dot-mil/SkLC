# Operator kit

The operator kit provides assessment tooling, site source, and a reference GitLab
pipeline for building and deploying an organization's skill exchange. A reference
skill catalog is included to support initial setup. SkillSpector is installed separately.

## Install

Download `deployment-kit-operator-<version>.zip` from SkLC GitHub Releases and
compare its SHA-256 with GitHub's asset digest. Extract into an empty GitLab
project, including `.gitlab-ci.yml` and `.exchange/`, and commit the contents.

## Configure the catalog

Operators can retain, extend, or replace the included reference catalog. Place each
skill package under `skills/<namespace>/<skill>/`, including its `SKILL.md` and
supporting files. The pipeline discovers and processes the packages present in that
directory. Each `SKILL.md` must declare a name matching its skill directory and a
nonempty description. The included catalog uses the `ai4sdlc` namespace; operators
can use their own namespaces for additional or replacement catalogs.

Configure catalog categories, tags, and display settings through `.exchange/`.
Native assessment findings inform the site's risk display. Publication decisions
remain with the organization operating the exchange.

## Configure the environment

Configure the assessment image and runner tags for the target environment using
GitLab CI/CD variables. Review the supplied scan-mode and build-image defaults and
override them as needed.

| Variable | Purpose and default |
| --- | --- |
| `ASSESSMENT_IMAGE` | Required: Linux image with Python 3.12+, pip, Git, and external SkillSpector `>=2.10,<3` on PATH; 2.10.0 is tested |
| `ASSESSMENT_RUNNER_TAG` | Required: trusted container runner with assessor/provider access |
| `BUILD_RUNNER_TAG` | Required: container runner able to install npm dependencies |
| `PAGES_RUNNER_TAG` | Required: runner allowed to publish GitLab Pages |
| `SCAN_MODE` | `llm-assisted` (default) or explicitly `static-only` |
| `NODE_IMAGE` | Defaults to `node:22`; replacement must provide Node >=22.22.0 and npm |
| `PAGES_IMAGE` | Defaults to `alpine:3.24.2`; replace for your registry if needed |

For LLM-assisted assessment, configure the provider/model and masked credentials
described in [assessment-kit setup](docs/assessment-kit.md). Give these only to
trusted runners and reviewed default-branch content. Static-only makes no LLM
requests. Runners need access to configured image/package registries and any
selected provider; the ZIP is not an offline dependency bundle. Enable GitLab Pages.

## Run and retain results

The supplied pipeline runs when manually started on the default branch through
**Build > Pipelines > New pipeline**. Operators can adapt the reference CI
configuration to their organization's workflow and access controls.

Jobs run advice, formal assessment, verified data generation, site build, then
Pages deployment. Native reports, adjudication and logs are retained as artifacts;
advice creates no BOE. Assessment creates `evidence/<namespace>/<skill>/index.json`
with content hashes and report digests. Generation rejects stale or changed evidence.
Failures stop dependent jobs; available advice/evidence artifacts remain for diagnosis.
Successful scans with findings remain successful execution, not approval to publish.

Advice and evidence artifacts expire after 30 days by default. Download them before
expiry; commit evidence manually if you want durable history. The pipeline never
commits or pushes. A fresh run without persisted evidence reassesses the catalog.
Persisted assessments for unchanged skill contents require an explicit `--override`
when invoking assess again; the template never replaces them silently.

## Run locally

For local use, install the wheel into an activated Python environment, ensure
SkillSpector and Git are on PATH, and run from the extracted root:

```sh
python -m pip install wheels/*.whl
export PYTHONPATH=scripts
python -m skill_exchange.operator advise --evidence advice --scan-mode static-only
python -m skill_exchange.operator assess --scan-mode static-only
python -m skill_exchange.operator generate --scan-mode static-only
npm ci --prefix site
npm --prefix site run build
```

Operator commands accept `--skills`, `--evidence`, `--policy`, and `--generated`
paths; advice uses `--evidence` as its report-output root. When changing the generated
path, set `SKILL_EXCHANGE_GENERATED_ROOT` to that same absolute path for the Node build.
For source links outside CI, set `SKILL_EXCHANGE_SOURCE_REPOSITORY_URL` and
`SKILL_EXCHANGE_SOURCE_BRANCH` to the installed catalog's repository and revision.

Missing scanner/provider errors: inspect the retained logs and assessment setup.
Invalid BOE: restore the matching skill/reports, or explicitly reassess; do not edit
hashes to bypass verification. Missing site data: confirm the generation job succeeded
and its artifact reached the build job. Pending jobs: check the configured runner
tags/images. Pages publishes the generated `public/` directory unchanged.
