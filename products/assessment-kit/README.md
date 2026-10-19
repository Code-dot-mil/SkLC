# Assessment kit

Validate a local skill directory and get advisory scan findings with
`skill-assessment validate` and `skill-assessment advise`.

## Prerequisites

Python 3.12 or later is required. The examples below use `uv` to build and install
the assessment kit and run its commands.

### SkillSpector

SkillSpector is an external prerequisite. The `validate` command does not require it.
The compatibility target is SkillSpector `>=2.10,<3`, using its public CLI and JSON
report format. Integration has been tested with 2.10.0; compatibility with later
v2 releases is expected, not individually verified.

The `skillspector` executable must be available on `PATH` in the environment that
runs assessment-kit. Follow [SkillSpector's installation guidance](https://github.com/NVIDIA/SkillSpector#installation).
Its installation and dependency management are outside this repository's scope;
the assessment-kit wheel does not install it.

`uv tool install` exposes the executable through uv's tool executable directory.
That directory must be on `PATH`; if uv warns that it is missing, run
`uv tool update-shell` and restart the shell. A `uv pip install` or source install
instead requires the installation environment's executable directory on `PATH`,
usually by activating that environment. See [uv's tool executable documentation](https://docs.astral.sh/uv/concepts/tools/#tool-executables).
Verify availability from the shell used to run assessment-kit:

```sh
skillspector --version
```

Configure SkillSpector's
[provider environment](https://github.com/NVIDIA/SkillSpector/tree/v2.10.0#configuration)
for default LLM-assisted scans; skill contents are sent to that provider. Advise
also uses that configuration for a separate finding-adjudication request.

### Adjudication gateways

Set `SKILLSPECTOR_MODEL` explicitly. Adjudication supports these existing
SkillSpector configurations, without importing SkillSpector or installing its SDKs:

| `SKILLSPECTOR_PROVIDER` | Configuration |
| --- | --- |
| `openai` | `OPENAI_API_KEY`; optional `OPENAI_BASE_URL` (defaults to the OpenAI API) and `OPENAI_PROJECT_ID` |
| `openai_compatible` | `SKILLSPECTOR_COMPAT_API_KEY` and `SKILLSPECTOR_COMPAT_BASE_URL` |
| `azure_openai` | `AZURE_OPENAI_API_KEY` and `AZURE_OPENAI_ENDPOINT`; optional `AZURE_OPENAI_DEPLOYMENT` (defaults to model) and `AZURE_OPENAI_API_VERSION` (defaults to `2024-06-01`, matching SkillSpector 2.10.0) |

For an OpenAI-compatible gateway, the base URL includes its API prefix, such as
`https://gateway.example/v1`. For Azure deployment routing, the endpoint is the
resource or gateway prefix before `/openai/deployments/...`; authentication uses
the `api-key` header. An Azure gateway exposing the OpenAI-compatible v1 protocol
instead uses the `openai` configuration. Gateways must use HTTPS and accept chat
completions with JSON-object output and `max_completion_tokens`.

Adjudication does not switch providers or models automatically. Unsupported
providers or missing configuration produce an explicit unavailable adjudication.

## Installation

Download `skill_assessment-<version>-py3-none-any.whl` from
[SkLC releases](https://github.com/Code-dot-mil/SkLC/releases). Calculate the file's
SHA-256 and compare it with the asset digest GitHub displays before installing.
The Python package version matches the release version under Python packaging
normalization. The wheel installs assessment-kit and PyYAML; install SkillSpector
separately for Advise and Assess. Validate needs no scanner.

To build from source instead, run from the repository root:

```sh
uv build --wheel products/assessment-kit --out-dir release/assessment-kit
```

Copy the wheel into a separate working directory, then install it:

```sh
uv venv --python 3.12
uv pip install skill_assessment-0.1.0-py3-none-any.whl
```

## Validate

Validate one local skill directory. Validation requires
a readable UTF-8 `SKILL.md` with YAML frontmatter containing nonempty string
fields `name` and `description`. The name must match the directory name.
Additional metadata is allowed. Validation does not execute skill content or
assess its safety.

```sh
uv run --no-project skill-assessment validate --skill ./my-skill
```

The command accepts a single directory, without a namespace or repository layout
requirement. Validation reads no exchange policy and makes no scanner or provider calls.
Exit status is `0` for valid input, `1` for invalid or unreadable input, and `2`
for incorrect command usage. Diagnostics go to standard error on failure.

## Advise

Validate and scan one local skill directory using SkillSpector. Complete the
[SkillSpector prerequisites](#skillspector) before running this command.
LLM-assisted scanning is the default.

```sh
uv run --no-project skill-assessment advise --skill ./my-skill
uv run --no-project skill-assessment advise --skill ./my-skill --scan-mode static-only --output-dir ./reports
```

By default, scans use LLM analysis. Use `--scan-mode static-only` to scan without
an LLM. If LLM analysis fails, the command reports an error instead of switching
to static scanning.

Each scan checks the selected skill. The scanner and subsequent adjudication request
each have a 5-minute timeout by default. Use `--timeout SECONDS` to change each
limit to a positive whole number of seconds. For example, `--timeout 600` allows
up to 10 minutes per stage.

Each run creates a new directory inside `./assessment-reports/`, or inside the
directory you specify with `--output-dir`. This location must be outside the skill.
The command displays retained report paths. `skillspector.json` preserves the raw
native report; `scanner.log` retains diagnostics. Both scan modes produce
`adjudication.json` with the same fields: findings, safety and coverage judgments,
status, scope, and inference metadata. LLM-assisted runs adjudicate each finding.
Static-only runs record `status: not_performed`, null safety and coverage judgments,
and `not_adjudicated` entries preserving each finding's index and rule ID.
Provider and model fields and token usage are null, inference call counts and
duration are zero, and the creation timestamp records when the artifact was written.
Static-only runs make no adjudication request, even when provider credentials are
configured. Existing runs and skills stay unchanged.

**MVP: adjudication examines SKILL.md and scanner evidence only; additional skill
files are not independently reviewed.** The full SKILL.md is sent in one request,
without execution, following links, secret redaction, or chunking. A model's
`safe_to_use: true` is limited to that scope and does not certify the package.
Assessment-kit does not truncate inputs; gateway context-limit errors produce a
failed adjudication.

The system prompt is packaged in
[`prompts/adjudicate.md`](https://github.com/Code-dot-mil/SkLC/blob/main/products/assessment-kit/src/skill_assessment/prompts/adjudicate.md). It explains
static confidence, `llm-unconfirmed`, benign-context tags, and ledger exceptions.
The response is checked for a verdict on every finding and consistency between
the safety flag, findings, and coverage. The adjudication adds code-generated
status, scope, provider/model, timestamp, duration, attempted/successful call
counts, and token usage when the gateway supplies it. Unknown usage is not zero.
Credentials and endpoint URLs are not included in adjudication metadata.

Readable partial LLM-assisted scans still reach adjudication, but retain their incomplete
scanner status and exit code 3. Missing configuration produces `status: unavailable`;
request or response failures produce `status: failed`. Both use `safe_to_use: null`,
unknown coverage, and `not_adjudicated` findings with a brief reason. Scanner
failures also produce an unavailable adjudication in LLM-assisted mode when artifacts
can be written. Static-only failures retain `status: not_performed`, with any readable
findings, or an empty findings list when no usable report exists. Scan failure and
incompleteness still return exit code 3 in either mode; `not_performed` alone is not
an execution failure. Raw scanner reports are retained only if the scanner emitted them.

Exit status is `0` when Advise completes, regardless of finding severity, `1` for
invalid input or output setup, `2` for incorrect usage, and `3` for a missing scanner,
scanner failure, timeout, missing/malformed output, incomplete coverage, or
unavailable/degraded requested LLM analysis, or unavailable/failed adjudication.
A completed negative safety verdict remains advisory and does not change a successful
exit to an execution error. A successful exit does not certify safety.
Advise creates no BOE or exchange evidence.

## Assess

`assess` scans a local skill, produces an adjudication, and records the reports in
the skill’s assessment history.

```sh
uv run --no-project skill-assessment assess --skill ./my-skill --output-dir ./evidence/my-skill
uv run --no-project skill-assessment assess --skill ./my-skill --output-dir ./evidence/my-skill --override --scan-mode static-only
```

Each successful assessment retains `skillspector.json`, `adjudication.json`, and
`scanner.log`. The index holds one assessment per `skill_sha256`, regardless of
scan mode. Assessing unchanged content returns an error without scanning; use
`--override` to replace its indexed assessment. Changed skill content adds a new
hash entry, retaining assessments for other hashes.

The index lists assessments newest first. Each path is relative to the index;
consumers read metadata from the entry rather than deriving it from directory names.

```json
{
  "boe_schema_version": 1,
  "skill": "my-skill",
  "assessments": [
    {
      "assessed_at": "2026-10-19T15:42:08Z",
      "path": "my-skill-example",
      "skill_sha256": "<64 hexadecimal characters>",
      "reports": {
        "skillspector.json": "<SHA-256>",
        "adjudication.json": "<SHA-256>",
        "scanner.log": "<SHA-256>"
      }
    }
  ]
}
```

`skill_sha256` records the skill's file paths and contents as metadata. It hashes
sorted relative POSIX file paths and contents, each prefixed by its unsigned
eight-byte big-endian byte length, following `skill-assessment-package-v1` and a
NUL byte. Empty directories are omitted.

`--scan-mode` and `--timeout` have the same behavior as in `advise`. If scanning
or adjudication fails, diagnostics and available outputs are retained, and the
index and any previous assessment remain unchanged. Exit codes match `advise`;
duplicate assessments without `--override` and index read or write errors return `1`.

`reports` records each output's SHA-256; hashes are not automatically verified.

## Reference GitLab CI

Include `ci/gitlab/profile.yml` (`ci/assessment.yml` in the operator ZIP) for
`.skill-advice` and `.skill-assessment`. Put the wheel in `wheels/` and set
`ASSESSMENT_IMAGE`, `ASSESSMENT_RUNNER_TAG`, `SKILL_DIRECTORY`, `SCAN_MODE`,
`ADVICE_OUTPUT`, and `ASSESSMENT_OUTPUT`. The including pipeline defines triggers
and artifact retention.

## Python callers

Python callers can catch `ScanTimeoutError` to decide whether to retry and
`OutputDirectoryError` to choose or repair the output location. `IncompleteScanError`
identifies partial or degraded analysis. Timeout and incomplete-analysis errors
inherit from `ScanError`, which also covers missing scanners, process failures,
and unreadable or malformed reports. Error types live in `skill_assessment.errors`.

## Development

`uv run --extra test pytest` runs without installing SkillSpector.
The real static scan integration test runs only when `skillspector` is on `PATH`;
other Advise tests exercise the external process and HTTP boundaries without a
scanner install or provider credentials.
