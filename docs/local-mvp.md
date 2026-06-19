# Local Static Exchange MVP

This repository can run the Step 1 skill exchange MVP locally without GitLab.

## Commands

Run tests:

```sh
uv run --extra test pytest
```

Generate a mock MR assessment:

```sh
uv run python -m skill_exchange.cli mock-mr-scan --mr 1 --scan-mode static-only
```

Generate official local exchange evidence for both static-only and LLM-assisted SkillSpector configurations:

```sh
uv run python -m skill_exchange.cli publish-local
```

Generate only one configuration when needed:

```sh
uv run python -m skill_exchange.cli publish-local --scan-mode static-only
uv run python -m skill_exchange.cli publish-local --scan-mode llm-assisted
```

Build the static site:

```sh
npm --prefix site install
npm --prefix site run build
```

## Local Mock Outputs

- `.gitlab-mock/mr/<id>.md.jsonl` records mock MR and pipeline events.
- `.gitlab-mock/mr-artifacts/<id>/<run-id>/comment.md` is the reviewer-facing assessment comment.
- `.exchange/generated/index.json` is the exchange data contract.
- `.exchange/generated/tables/scanner_runs.json` records scanner executions.
- `.exchange/generated/tables/scanner_artifacts.json` points to native scanner output, summaries, and BOE files.
- `.exchange/generated/tables/scanner_findings.json` stores scanner findings while preserving each native finding object.
- `.exchange/generated/boe/` stores official local BOE records.
- `.exchange/generated/zips/` stores runtime skill zip downloads.

## SkillSpector

The local harness runs a real SkillSpector binary. Put `skillspector` on `PATH`, or set `SKILLSPECTOR_BIN` to the binary from your local fork before running scan or publish commands.

For LLM-assisted scans, provide provider credentials and endpoint variables in the shell running the command. The harness maps `SKILL_EXCHANGE_LLM_API_KEY`, `SKILL_EXCHANGE_LLM_BASE_URL`, `SKILL_EXCHANGE_LLM_MODEL`, and `SKILL_EXCHANGE_LLM_PROVIDER` into the OpenAI-compatible and SkillSpector-native environment expected by SkillSpector. You can also set SkillSpector-native variables directly. The harness does not print the API key.

## Boundaries

The local mock does not implement GitLab API behavior, merge restrictions, approval rules, protected branches, or bot authentication. It exists to prove the exchange building blocks before real GitLab integration.
