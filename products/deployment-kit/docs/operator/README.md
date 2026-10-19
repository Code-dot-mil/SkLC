# Operator kit

Assess an organization's skill catalog and build its exchange using the supplied GitLab pipeline.

## Install

Download `deployment-kit-operator-<version>.zip` from SkLC GitHub Releases and
compare its SHA-256 with GitHub's asset digest. Extract into an empty GitLab
project, including `.gitlab-ci.yml` and `.exchange/`, and commit the contents.

Retain, extend, or replace the reference catalog under `skills/ai4sdlc/`.
Place packages in `skills/<namespace>/<skill>/`, including supporting files and a
`SKILL.md` with a matching name and nonempty description. Configure categories,
tags, and display settings through `.exchange/`.

## Configure the environment

Set the required GitLab CI/CD variables; override defaults as needed.

| Variable | Purpose and default |
| --- | --- |
| `ASSESSMENT_IMAGE` | Required: Linux image with Python 3.12+, pip, Git, and external SkillSpector `>=2.10,<3` on PATH; 2.10.0 is tested |
| `ASSESSMENT_RUNNER_TAG` | Required: trusted container runner with assessor/provider access |
| `BUILD_RUNNER_TAG` | Required: container runner able to install npm dependencies |
| `PAGES_RUNNER_TAG` | Required: runner allowed to publish GitLab Pages |
| `SCAN_MODE` | `llm-assisted` (default) or explicitly `static-only` |
| `NODE_IMAGE` | Defaults to `node:22`; replacement must provide Node >=22.22.0 and npm |
| `PAGES_IMAGE` | Defaults to `alpine:3.24.2`; replace for your registry if needed |

Install SkillSpector separately and configure providers and masked credentials using
[assessment-kit setup](docs/assessment-kit.md). Use trusted runners for reviewed content.
Runners need registry/package and selected-provider access. Enable GitLab Pages.

## Run and retain results

Start **Build > Pipelines > New pipeline** on the default branch. The supplied CI
runs advice, assessment, generation, build, then Pages deployment; failures stop dependent jobs.
Generation reads the newest entry in `evidence/<namespace>/<skill>/index.json`
without verifying hashes. Assess after changing skills and retain the matching outputs.

Advice and evidence artifacts expire after 30 days. Download them or commit them
manually for durable history; the pipeline makes no commits or pushes. See the
[assessment guide](docs/assessment-kit.md#assess) for history and `--override` behavior.

## Run locally

Activate a Python environment with SkillSpector and Git on PATH, then run from the extracted root:

```sh
python -m pip install wheels/*.whl
export PYTHONPATH=scripts
python -m skill_exchange.operator advise --evidence advice --scan-mode static-only
python -m skill_exchange.operator assess --scan-mode static-only
python -m skill_exchange.operator generate --scan-mode static-only
npm ci --prefix site
npm --prefix site run build
```

Paths are configurable with `--skills`, `--evidence`, `--policy`, and `--generated`;
advice uses `--evidence` for its reports. For a custom generated path, set
`SKILL_EXCHANGE_GENERATED_ROOT` to the same absolute path for Node.
Outside CI, set `SKILL_EXCHANGE_SOURCE_REPOSITORY_URL` and `SKILL_EXCHANGE_SOURCE_BRANCH`
to the catalog repository and revision for source links.
