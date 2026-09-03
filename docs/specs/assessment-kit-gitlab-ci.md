# Assessment Kit GitLab CI Profile Spec

## Decision baseline

This spec follows `docs/decisions.md`: customer automation runs in GitLab, while maintainer release workflows remain separate in GitHub.

## Milestone

`docs/roadmap.md` section 3.5, Assessment-kit later release - GitLab CI profile.

## Status

Approved.

## Outcome

A customer uses a released assessment-kit GitLab CI profile for skill advice and assessment without designing CI jobs.

## Release artifact

The assessment-kit release adds:

- Minimal GitLab CI profile at `.gitlab/assessment-kit.gitlab-ci.yml`.
- Advice job documentation.
- Assessment job documentation.
- Required variable and runner documentation.
- Manual BOE persistence guidance.
- Updated release manifest and checksums.

The profile is shipped with that exact path and filename so a customer can copy
it unchanged into a GitLab project and include it from the project's root
`.gitlab-ci.yml`:

```yaml
include:
  - local: .gitlab/assessment-kit.gitlab-ci.yml
```

The include file must be present in the repository when GitLab creates the
pipeline. It cannot be downloaded by a job in the same pipeline before include
resolution.

## CI profile contract

The shipped profile defines exactly two jobs:

| Job | Stage | Purpose |
|---|---|---|
| `assessment_kit_advise` | `skill_advice` | Validate configured skills, run `advise`, and retain author-facing advice and native assessor reports. |
| `assessment_kit_assess` | `skill_assessment` | Validate configured skills, run `assess`, retain native assessor reports and BOE, then verify the BOE. |

The profile declares these stages in this order:

```yaml
stages:
  - skill_advice
  - skill_assessment
```

Projects that already declare stages must add `skill_advice` and
`skill_assessment` in the desired order before including or extending the
profile.

## Required configuration

The profile fails closed during preflight when required configuration is absent.
It does not infer local defaults for credentials, runner routing, assessor
access, or release provenance.

Required variables:

| Variable | Description |
|---|---|
| `SKLC_SKILL_ROOT` | Root directory containing skill packages to pass as `--root`. |
| `SKLC_ASSESSOR` | Supported assessor identifier or profile name consumed by the released CLI. |
| `SKLC_ADVICE_RUNNER_TAG` | Generic GitLab runner tag for the advice job. |
| `SKLC_ASSESSMENT_RUNNER_TAG` | Generic GitLab runner tag for the assessment job. |

Exactly one assessment-kit install source is required:

| Variable | Description |
|---|---|
| `SKLC_ASSESSMENT_KIT_URL` | URL for the released assessment-kit archive to download and install in the job. |
| `SKLC_ASSESSMENT_KIT_PATH` | Local path to an assessment-kit archive or wheel already present in the job workspace. |
| `SKLC_ASSESSMENT_KIT_SHA256` | Expected SHA-256 digest for the selected archive or wheel. Required for URL installs and optional for local-path installs. |

Preflight fails when neither `SKLC_ASSESSMENT_KIT_URL` nor
`SKLC_ASSESSMENT_KIT_PATH` is set, or when both are set. URL installs
must verify `SKLC_ASSESSMENT_KIT_SHA256` before installation.
Local-path installs must verify `SKLC_ASSESSMENT_KIT_SHA256` when it
is set. The profile must not fall back to a globally installed
`skill-assessment` executable.

Required secret variables depend on the selected assessor. The documentation
must use generic names and map them to the released CLI's supported assessor
settings. For SkillSpector, the documentation must link to the NVIDIA
SkillSpector source at `https://github.com/NVIDIA/SkillSpector`.

| Variable | Description |
|---|---|
| `SKLC_LLM_API_KEY` | Masked credential for assessor model access when the assessor requires one. |
| `SKLC_LLM_BASE_URL` | Base URL for assessor model access when the assessor requires a non-default endpoint. |
| `SKLC_LLM_MODEL` | Model or deployment name when the assessor requires an explicit model setting. |
| `SKLC_LLM_PROVIDER` | Provider identifier when the assessor requires one or when the default provider is not intended. |

Supported optional variables:

| Variable | Default | Description |
|---|---|---|
| `SKLC_ADVICE_OUTPUT_DIR` | `assessment-kit/advice` | Directory retained by the advice job. |
| `SKLC_ASSESSMENT_OUTPUT_DIR` | `assessment-kit/assessment` | Directory retained by the assessment job. |
| `SKLC_SKILLSPECTOR_SCAN_MODE` | `llm-assisted` | Assessment-kit environment variable for the `skillspector` assessor scan mode. Supported values are `llm-assisted` and explicit `static-only`. |

The release documentation must explain that `SKLC_SKILL_ROOT` maps to
the CLI's `--root` argument. It must show the expected skill-root tree, where
each discovered skill package has its own `SKILL.md`, and must show the advice
and assessment artifact layouts produced by the default output directories.

Secrets must be configured as masked GitLab CI/CD variables, protected when the
project's branch protection model allows it. The profile must not echo secret
values, write them into artifacts, accept them through committed files, or print
the full environment. Jobs pass credentials to the assessment CLI through
environment variables only.

Runner tags are generic customer-provided tags. The release documentation must
not name maintainer-specific runners or secret variables. If advice and
assessment require different network access, the customer sets different values
for `SKLC_ADVICE_RUNNER_TAG` and
`SKLC_ASSESSMENT_RUNNER_TAG`; otherwise they may use the same generic
tag. The advice job uses `tags: ["$SKLC_ADVICE_RUNNER_TAG"]`, and
the assessment job uses `tags: ["$SKLC_ASSESSMENT_RUNNER_TAG"]`.

## CI behavior

- Both jobs resolve exactly one assessment-kit install source. URL installs
  download `SKLC_ASSESSMENT_KIT_URL` and verify
  `SKLC_ASSESSMENT_KIT_SHA256`. Local-path installs use
  `SKLC_ASSESSMENT_KIT_PATH` and verify
  `SKLC_ASSESSMENT_KIT_SHA256` when provided. Both jobs install the
  resolved CLI and fail before assessment if source selection, checksum
  verification, or installation fails.
- Both jobs run
  `skill-assessment validate --root "$SKLC_SKILL_ROOT"` before
  invoking assessor behavior.
- Both jobs pass `SKLC_ASSESSOR` as the `--assessor` command argument and pass
  assessment-kit environment variables such as `SKLC_SKILLSPECTOR_SCAN_MODE`
  and `SKLC_LLM_*` through the process environment.
- Advice invokes the released CLI as
  `skill-assessment advise --root "$SKLC_SKILL_ROOT" --assessor "$SKLC_ASSESSOR" --output "$SKLC_ADVICE_OUTPUT_DIR"`.
- Advice retains native assessor reports under
  `$SKLC_ADVICE_OUTPUT_DIR/native/` and author advice at
  `$SKLC_ADVICE_OUTPUT_DIR/advice.md`.
- Advice job does not create BOE and must fail if a BOE path is produced under
  `SKLC_ADVICE_OUTPUT_DIR`.
- Assessment invokes the released CLI as
  `skill-assessment assess --root "$SKLC_SKILL_ROOT" --assessor "$SKLC_ASSESSOR" --boe-root "$SKLC_ASSESSMENT_OUTPUT_DIR/boe"`.
- Assessment retains native assessor reports and updated BOE manifests under
  `$SKLC_ASSESSMENT_OUTPUT_DIR/boe/`.
- Assessment verifies every retained BOE manifest with the released `verify-boe`
  command before the job succeeds.
- Jobs make no source-control changes. They must not run `git add`,
  `git commit`, `git push`, GitLab API writes, or equivalent persistence steps.

Both jobs retain artifacts with `when: always` so failed assessor runs leave
diagnostics, but job success still depends on the command exit status and
post-run checks. Neither job uses `allow_failure`.

## Assessment-kit configuration in CI

The profile does not generate an assessment-kit config file from environment
variables. For each supported assessment-kit setting, the released CLI applies
normal precedence:

```text
command argument > environment variable > config file > documented default
```

For the first release, the profile passes `SKLC_ASSESSOR` as the `--assessor`
command argument, and the supported value is `skillspector`. Preflight rejects
any `SKLC_SKILLSPECTOR_SCAN_MODE` value other than `llm-assisted` or
`static-only`. When `llm-assisted` is selected or defaulted, the required
`SKLC_LLM_*` variables for the configured provider must be present before the
CLI runs. When `static-only` is explicitly selected, those variables may be
absent. The profile must not fall back to `static-only` when `llm-assisted` is
selected or defaulted but its required environment variables are unavailable.

Jobs pass secret values only through the process environment.

The profile exposes only the documented variables used in its command assembly
and does not provide arbitrary CLI passthrough. Additional assessor options
require documented CLI environment variables or an explicit documented config
path option plus documented preflight validation.

During preflight, each job also writes `.assessment-kit/skill-map.json` by
recursively discovering every valid skill package under
`SKLC_SKILL_ROOT`. The file maps standard skill names to paths
relative to `SKLC_SKILL_ROOT`:

```json
{
  "python-secure-code-review": "ai4sdlc/python-secure-code-review"
}
```

Discovery fails before assessor execution when any selected package is invalid,
two packages resolve to the same skill name, or a relative path escapes
`SKLC_SKILL_ROOT`.

## BOE verification loop

After `assess` completes, `assessment_kit_assess` verifies each BOE directory
with this logic:

```text
for each directory matching "$SKLC_ASSESSMENT_OUTPUT_DIR/boe/"*/:
  skill_name = basename(directory)
  relative_path = skill-map[skill_name]
  require relative_path exists
  skill_path = "$SKLC_SKILL_ROOT/$relative_path"
  require "$skill_path/SKILL.md" exists
  run skill-assessment verify-boe --skill "$skill_path" "$directory"
  append stdout and stderr to "$SKLC_ASSESSMENT_OUTPUT_DIR/verify-boe.log"
```

The job fails when no BOE directories are produced for a non-empty skill root,
when any BOE directory name does not resolve to a selected skill package, or
when any `verify-boe` invocation exits non-zero. The loop must not infer skills
from BOE paths outside `$SKLC_ASSESSMENT_OUTPUT_DIR/boe/`.

## Artifact contract

The advice job publishes:

```text
$SKLC_ADVICE_OUTPUT_DIR/
  advice.md
  native/
```

The assessment job publishes:

```text
$SKLC_ASSESSMENT_OUTPUT_DIR/
  boe/
  verify-boe.log
```

The profile must keep native assessor reports unchanged. BOE manifests record
report paths relative to each `boe.json` directory and SHA-256 digests produced
by the released assessment CLI. The retained advice and assessment artifact
trees conform to the assessment-artifacts v1 contract.

## Manual BOE persistence

The release documentation explains how a developer manually reviews the
assessment job artifacts, copies accepted files from
`$SKLC_ASSESSMENT_OUTPUT_DIR/boe/` into the target repository
locations, and commits them using the customer's normal source-control process.
The CI profile itself never persists BOE back to the repository.

## Pass and fail behavior

Advice fails when required variables are missing, checksum verification fails,
the skill root is missing, `validate` exits non-zero, `advise` exits non-zero,
required advice artifacts are missing, or BOE is produced.

Assessment fails when required variables are missing, checksum verification
fails, the skill root is missing, `validate` exits non-zero, `assess` exits
non-zero, required report or BOE artifacts are missing, or `verify-boe` exits
non-zero for any retained BOE manifest.

When the CLI exits `10` for a retryable assessor execution failure, including
`llm-assisted` LLM rate limiting such as HTTP `429`, the job fails with that
status so GitLab retry controls can retry the job. The profile must not switch
to `static-only`, mark the job successful, or create BOE for the failed
skill/assessor pair.

Assessment succeeds only when `verify-boe` accepts the retained BOE and the job
has made no source-control changes.

## Contracts

The CI profile consumes the assessment-kit CLI and its contracts. It does not create a new product contract.

## GitLab proof

Acceptance requires a clean GitLab project that:

1. Receives the assessment-kit release from GitHub Releases.
2. Verifies the checksums.
3. Configures the shipped GitLab CI profile.
4. Proves URL install and local-path install source selection in separate jobs
   or separate pipeline runs.
5. Runs advice and assessment jobs.
6. Retains documented artifacts.

## Exclusions

- Catalog assembly.
- Site build or deployment.
- Maintainer GitHub Actions.
- Merge-request comments.
- Bot-driven BOE commits.
