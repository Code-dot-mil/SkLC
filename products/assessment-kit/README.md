# Assessment kit

Validate one local skill directory with Python 3.12 or later. Validation requires
a readable UTF-8 `SKILL.md` with YAML frontmatter containing nonempty string
fields `name` and `description`. The name must match the directory name.
Additional metadata is allowed. Validation does not execute skill content or
assess its safety.

From the repository root, build the wheel:

```sh
uv build --wheel products/assessment-kit --out-dir release/assessment-kit
```

Copy the wheel into a separate working directory, then install and run it:

```sh
uv venv --python 3.12
uv pip install skill_assessment-0.1.0-py3-none-any.whl
uv run --no-project skill-assessment validate --skill ./my-skill
```

The command accepts a single directory, without a namespace or repository layout
requirement. Validation reads no exchange policy and makes no scanner or provider calls.
Exit status is `0` for valid input, `1` for invalid or unreadable input, and `2`
for incorrect command usage. Diagnostics go to standard error on failure.

## Advice

SkillSpector is an external prerequisite for `advise`. The compatibility target
is SkillSpector `>=2.10,<3`, using its public CLI and JSON report format. Integration
has been tested with 2.10.0; compatibility with later v2 releases is expected,
not individually verified.

The `skillspector` executable must be available on `PATH` in the environment that
runs assessment-kit. Follow [SkillSpector's installation guidance](https://github.com/NVIDIA/SkillSpector#installation).
Its installation and dependency management are outside this repository's scope;
the assessment-kit wheel does not install it. Validation does not require it.

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
for default LLM-assisted scans; skill contents are sent to that provider.

```sh
uv run --no-project skill-assessment advise --skill ./my-skill
uv run --no-project skill-assessment advise --skill ./my-skill --scan-mode static-only --output-dir ./reports
```

Static scanning is explicit and never a fallback. After validation, SkillSpector's
CLI runs once with a five-minute timeout and default settings, without recursive
or transitive scanning or author-supplied baselines.

Each run prints its unique directory under `./assessment-reports/` or `--output-dir`,
which must be outside the skill. `skillspector.json` retains native findings,
locations, explanations, and remediations; `scanner.log` retains diagnostics.
Failures preserve available reports and logs. Existing runs and skills stay unchanged.

Exit status is `0` for completed advice regardless of finding severity, `1` for
invalid input or output setup, `2` for incorrect usage, and `3` for a missing scanner,
scanner failure, timeout, missing/malformed output, incomplete coverage, or
unavailable/degraded requested LLM analysis. A successful exit does not certify safety. Advice creates
no BOE or exchange evidence.

Python callers can catch `ScanTimeoutError` to decide whether to retry and
`OutputDirectoryError` to choose or repair the output location. `IncompleteScanError`
identifies partial or degraded analysis. Timeout and incomplete-analysis errors
inherit from `ScanError`, which also covers missing scanners, process failures,
and unreadable or malformed reports. Error types live in `skill_assessment.errors`.

For development, `uv run --extra test pytest` runs without installing SkillSpector.
The real static scan integration test runs only when `skillspector` is on `PATH`;
other advice tests exercise the external process boundary without a scanner install.
