# Assessor configuration

The first release supports NVIDIA
[SkillSpector](https://github.com/NVIDIA/SkillSpector) version `2.10.0`, source
revision `e29b16d305b0e738e3d4b952ba102f5522a6f084`. Install that executable on
`PATH` or set `SKILLSPECTOR_BIN` to its executable path.

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
export SKLC_LLM_API_KEY=<secret>
export SKLC_LLM_BASE_URL=https://llm.example/v1
export SKLC_LLM_MODEL=<model>
skill-assessment assess --skill <skill-directory> \
  --assessor skillspector --boe-root <boe-root>
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
skill-assessment assess --skill <skill-directory> \
  --assessor skillspector --config static.json --boe-root <boe-root>
```

The adapter maps the four `SKLC_LLM_*` variables to
`SKILLSPECTOR_PROVIDER`, `SKILLSPECTOR_COMPAT_API_KEY`,
`SKILLSPECTOR_COMPAT_BASE_URL`, and `SKILLSPECTOR_MODEL`. The selected values
override conflicting inherited native values. Secret values are redacted from
assessment-kit diagnostics.
