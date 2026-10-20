# Assessment kit

Assess a skill during development, understand which findings need action, and
check the revised skill. The kit produces a SkillSpector report and adjudication,
then translates them into a human-friendly, action-based summary.

After installation and provider setup:

```sh
skill-assessment assess --skill ./my-skill --output-dir ./reports
skill-assessment summarize --assessment-dir ./reports
```

Address confirmed findings and investigate unresolved findings, then assess the
revised skill with the same commands. False-positive determinations explain why
no remediation is needed for those findings. `validate` checks a package's
frontmatter; `hash` identifies its contents.

## Prerequisites

Python 3.12 or later is required. The examples below use `uv` to build and install
the assessment kit and run its commands.

### SkillSpector

SkillSpector is an external prerequisite. The `validate` command does not require it.
The compatibility target is SkillSpector `>=2.10,<3`, using its public CLI and JSON
report format. Integration has been exercised with 2.10.0 and 2.12.0; compatibility
with other v2 releases is expected, not individually verified.

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
for default LLM-assisted scans; skill contents are sent to that provider. Assess
also uses that configuration for a separate request to review the findings
(adjudication).

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
separately for Assess. Validate needs no scanner.

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

## Assess

### Run a scan

Validate and scan one local skill directory using SkillSpector. Complete the
[SkillSpector prerequisites](#skillspector) before running this command.
LLM-assisted scanning is the default. Assess checks for `skillspector` on `PATH`
before creating any files or directories, including when `--if-changed` is set.
If it is missing, the command exits with status `3`, creates no artifacts, and
leaves existing reports unchanged.

```sh
uv run --no-project skill-assessment assess --skill ./my-skill --output-dir ./reports
uv run --no-project skill-assessment assess --skill ./my-skill --scan-mode static-only --output-dir ./reports
```

By default, scans use LLM analysis. Use `--scan-mode static-only` to scan without
an LLM. If LLM analysis fails, the command reports an error instead of switching
to static scanning.

Each scan checks the selected skill. The scanner and subsequent adjudication request
each have a 5-minute timeout by default. Use `--timeout SECONDS` to change each
limit to a positive whole number of seconds. For example, `--timeout 600` allows
up to 10 minutes per stage.

### Reports and repeat runs

Select an output directory outside the skill with `--output-dir`. Each successful
assessment writes these files directly into it and displays the report paths:

| File | Contents |
| --- | --- |
| `skillspector.json` | The scanner's JSON report. |
| `adjudication.json` | A review of each finding, safety and coverage judgments, review status and scope, and provider and request details. |
| `scanner.log` | Scanner diagnostics. |

The BOE is the `skillspector.json` and `adjudication.json` pair. `scanner.log` is
diagnostic output and must not be committed or included in BOE packages.
Only these three output files are replaced. Other files in the output directory stay
untouched, and skill inputs stay unchanged. The adjudication's `skill_sha256`
field records the package hash described under [Hash](#hash).

By default, every invocation rescans. Add `--if-changed` to reuse successful
reports for the same skill contents and scan mode:

```sh
uv run --no-project skill-assessment assess --skill ./my-skill --output-dir ./reports --if-changed
```

Reuse requires the two JSON files and a matching package hash; diagnostics are optional. The scanner report
must show that scanning succeeded in the requested mode, and adjudication must
be completed (`not_performed` for static-only). Successful scans with coverage limitations can still qualify. Missing, malformed, failed, or mismatched reports
trigger a new scan.

The command prepares reports in a separate sibling directory before replacing
the current files. If scanning or adjudication fails, the current reports stay
unchanged; the error identifies the directory holding diagnostics and available
outputs. Replacement after a successful assessment happens one file at a time,
so it is not a transaction. Copy reports elsewhere if you need a lasting history;
the command keeps no history or assessment index.

### Shorten the source path

Use `--base-dir` (or `SKILL_ASSESSMENT_BASE_DIR` for CI) to remove a matching directory prefix from `skill.source` in the
native scanner report:

```sh
uv run --no-project skill-assessment assess --skill ./my-skill --output-dir ./reports --base-dir ./
```

An explicit `--base-dir` takes precedence over `SKILL_ASSESSMENT_BASE_DIR`.
The base directory resolves relative to the working directory. Absolute source
paths are normalized and matched at directory boundaries; a matching source
becomes relative to that base. Already-relative, unmatched, missing, or non-string
source values stay unchanged. Only `skill.source` is rewritten: other report
paths, finding text, and scanner logs are not redacted. Without either setting,
native report bytes stay unchanged.

The rewrite happens after scanning and before adjudication, including retained
failure reports when their JSON is usable. With `--if-changed`, qualifying cached
reports have a matching absolute source rewritten without another scan or provider
request. An already-relative cached source stays unchanged even if the base changes;
rescan without `--if-changed` to obtain a fresh source path.

### Review scope

**MVP NOTICE:** Adjudication examines `SKILL.md` and scanner evidence only.
Additional skill files are not independently reviewed. A `safe_to_use: true`
judgment applies only to this scope and does not certify the package.

The full `SKILL.md` is sent in one request. Assessment-kit does not execute it,
follow its links, redact secrets, split it into chunks, or truncate it. If the
input exceeds the gateway's context limit, adjudication fails.

### How findings are reviewed

The packaged
[system prompt](https://github.com/Code-dot-mil/SkLC/blob/main/products/assessment-kit/src/skill_assessment/prompts/adjudicate.md)
tells the model to treat skill text and scanner reports as evidence, never as
instructions. It asks for a true-positive, false-positive, or uncertain judgment
on every finding, with a reason. It explains how to read static confidence
scores, `llm-unconfirmed` and `benign-context` tags, and the scanner's record of
files and analysis it could not complete. These signals help the model judge the
findings; none establishes safety on its own.

Assessment-kit checks that the response covers every finding in order and that
the safety judgment agrees with the findings and coverage judgment. It adds the
review status and scope, provider and model, creation time, request duration,
call counts, and token usage when the gateway supplies it. Unknown token usage
is recorded as null, not zero. Credentials and endpoint URLs are excluded from
this metadata.

Static-only scans make no adjudication request, even if credentials are
configured. Their adjudication report uses `status: not_performed`, null safety
and coverage judgments, and `not_adjudicated` entries that keep each finding's
index and rule ID. Provider, model, and token usage are null; call counts and
duration are zero. The creation time records when the report was written.

### Coverage and failures

A readable scan with partial coverage still goes to adjudication. Reports can
be saved as the current assessment even with low coverage when the scanner
reports successful execution in the requested mode and adjudication completes.
The kit uses the scanner's execution outcome and inference metadata, rather than
reinterpreting its analyzer ledger. The scanner's coverage fields remain unchanged, and summaries retain
warnings about incomplete coverage.

Missing provider configuration produces `status: unavailable`. A failed request
or invalid response produces `status: failed`. Both leave safety and coverage
unknown (`null`) and mark findings `not_adjudicated` with a brief reason. A
scanner failure also produces an unavailable adjudication for an LLM-assisted
run when reports can be written. Static-only failures keep
`status: not_performed`, with any readable findings or an empty list if no usable
report exists. A scanner report is retained only if the scanner wrote one.

### Exit status

| Status | Meaning |
| --- | --- |
| `0` | Assessment completed, regardless of finding severity or negative safety and coverage judgments. |
| `1` | Invalid input or a problem setting up the output directory. |
| `2` | Incorrect command usage. |
| `3` | Missing scanner, scanner failure, timeout, missing or malformed output, failed or degraded requested LLM analysis, or unavailable or failed adjudication. |

`not_performed` alone is expected in static-only mode and does not signal a
failure. A successful exit does not certify safety.

## Hash

Print the package hash without running an assessment:

```sh
uv run --no-project skill-assessment hash --skill ./my-skill
```

Success writes only the SHA-256 and a newline to stdout. Invalid directories or
file read failures return `1` with diagnostics on stderr. This command hashes
package bytes without validating frontmatter.

The hash includes file paths and contents. It starts with
`skill-assessment-package-v1` and a NUL byte, then processes files in sorted
relative POSIX path order. Each path and each file's contents are preceded by
their unsigned eight-byte big-endian byte length. Empty directories are omitted.

## Summarize

Produce a human-friendly, action-based Markdown summary of the SkillSpector
report and adjudication:

```sh
skill-assessment summarize --assessment-dir ./reports > assessment.md
```

The directory must contain `skillspector.json` and `adjudication.json`. The summary
starts with the number of true-positive findings that need remediation, followed
by counts of unresolved findings and false positives. It includes the review
status, scope, and limitations. True positives and unresolved findings have detailed
entries; false positives have shorter entries. Findings from static-only scans
or unavailable or failed adjudication remain unresolved.

The command reads the reports without changing them. It needs no package hash or
scanner installation. Exit status is `0` for a rendered summary, `1` for
unreadable or mismatched reports, and `2` for incorrect command usage. Markdown
goes to stdout and errors go to stderr.

## Development

From this product directory, `uv run --extra test pytest` runs without installing
SkillSpector.
The real static scan integration test runs only when `skillspector` is on `PATH`;
other assessment tests exercise the external process and HTTP boundaries without
a scanner install or provider credentials.
