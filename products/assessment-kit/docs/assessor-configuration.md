# Assessor configuration

The first release supports NVIDIA
[SkillSpector](https://github.com/NVIDIA/SkillSpector) version `2.10.0`, source
revision `e29b16d305b0e738e3d4b952ba102f5522a6f084`. Install that executable on
`PATH` or set `SKILLSPECTOR_BIN` to its executable path. An explicitly blank
`SKILLSPECTOR_BIN` is an error; only an absent variable selects `PATH`.

Omitting `--config` uses `llm-assisted` mode and a 600-second timeout. A config
file is needed only to change these non-secret settings:

```json
{
  "assessors": {
    "skillspector": {
      "scan_mode": "llm-assisted",
      "timeout_seconds": 600
    }
  }
}
```

`SKLC_SKILLSPECTOR_SCAN_MODE` and `SKLC_SKILLSPECTOR_TIMEOUT_SECONDS` override
the corresponding file values. In `llm-assisted` mode, set all four secret or
endpoint variables: `SKLC_LLM_PROVIDER=openai_compatible`, `SKLC_LLM_API_KEY`,
`SKLC_LLM_BASE_URL`, and `SKLC_LLM_MODEL`. Static scanning must be selected
explicitly with `scan_mode: static-only` or
`SKLC_SKILLSPECTOR_SCAN_MODE=static-only`.

The precedence is environment variable, then config file, then documented
default. Command arguments control package selection and artifact locations;
there are no command-line settings for scan mode, timeout, or LLM secrets.
Unknown assessor blocks, unknown keys, unsupported values, and missing LLM
values fail closed before assessment.

For a default LLM-assisted run:

```text
export SKLC_LLM_PROVIDER=openai_compatible
export SKLC_SKILLSPECTOR_SCAN_MODE=llm-assisted
: "${SKLC_LLM_API_KEY:?Export your API key}"
: "${SKLC_LLM_BASE_URL:?Export your provider base URL}"
: "${SKLC_LLM_MODEL:?Export your model name}"
skill-assessment assess --skill workspace/team-a/secure-review \
  --assessor skillspector --boe-root assessment-output/boe
```

For an explicit static run, save this as `static.json`:

```json
{
  "assessors": {
    "skillspector": {
      "scan_mode": "static-only",
      "timeout_seconds": 600
    }
  }
}
```

Then run:

```text
unset SKLC_SKILLSPECTOR_SCAN_MODE SKLC_SKILLSPECTOR_TIMEOUT_SECONDS
skill-assessment assess --skill workspace/team-a/secure-review \
  --assessor skillspector --config static.json --boe-root assessment-output/boe
```

The adapter maps the four `SKLC_LLM_*` variables to
`SKILLSPECTOR_PROVIDER`, `SKILLSPECTOR_COMPAT_API_KEY`,
`SKILLSPECTOR_COMPAT_BASE_URL`, and `SKILLSPECTOR_MODEL`. The selected values
override conflicting inherited native values. Secret values are redacted from
assessment-kit diagnostics.

Paths in these examples match the tree in [commands](commands.md). Only
`scan_mode` and `timeout_seconds` are accepted config keys. The timeout must be
a positive integer; booleans, fractions, and null values are rejected.

Exit `10` requests a caller-managed retry for timeout, temporary assessor exit
`75`, HTTP `429` in LLM-assisted diagnostics, or degraded/unavailable LLM
coverage. Other execution failures return `2`. Each pair runs once. A batch
with any retryable failure returns `10`, even if another pair fails permanently;
inspect all diagnostics before retrying. No failure switches to static mode.
