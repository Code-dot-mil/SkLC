# Local Static Exchange MVP

This repository can run the Step 1 skill exchange MVP locally without GitLab.

## Commands

Run tests:

```sh
just test
```

Generate official local exchange evidence and derived site data for static-only SkillSpector:

```sh
just generate
```

`just generate` writes to `.exchange/local-generated/`. Use `--generated-dir` with the Python CLI only when you intentionally need a different output location.

Generate only one configuration when needed:

```sh
uv run python -m skill_exchange.cli publish-local --scan-mode static-only
uv run python -m skill_exchange.cli publish-local --scan-mode llm-assisted
```

Build the static site:

```sh
just build
```

## Local Generated Outputs

- `.exchange/generated/boe/` stores CI-produced durable BOE bundles, including supporting scanner output and summaries.
- `.exchange/local-generated/` stores ignored local generated data for development builds.
- `.exchange/generated/index.json` is a derived site data contract.
- `.exchange/generated/tables/scanner_runs.json` is a derived table of scanner executions.
- `.exchange/generated/tables/scanner_artifacts.json` is a derived table of native scanner output, summaries, and BOE download links.
- `.exchange/generated/tables/scanner_findings.json` is a derived table of scanner findings.
- `.exchange/generated/zips/` stores derived runtime skill zip downloads.

## SkillSpector

The local harness runs a real SkillSpector binary. Put `skillspector` on `PATH`, or set `SKILLSPECTOR_BIN` to the binary from your local fork before running scan or publish commands.

For LLM-assisted scans, provide provider credentials and endpoint variables in the shell running the command. The harness maps `SKILL_EXCHANGE_LLM_API_KEY`, `SKILL_EXCHANGE_LLM_BASE_URL`, `SKILL_EXCHANGE_LLM_MODEL`, and `SKILL_EXCHANGE_LLM_PROVIDER` into the OpenAI-compatible and SkillSpector-native environment expected by SkillSpector. You can also set SkillSpector-native variables directly. The harness does not print the API key.

## Boundaries

The local commands do not implement GitLab API behavior, merge restrictions, approval rules, protected branches, bot authentication, or Pages publication.
