# Local Static Exchange MVP

This repository can run the Step 1 skill exchange MVP locally without GitLab.

## Commands

Run tests:

```sh
uv run --extra test pytest
```

Generate a mock MR assessment:

```sh
uv run python -m skill_exchange.cli mock-mr-scan --mr 1 --scanner fixture --fixture skillspector-clean.json
```

Generate official local exchange evidence:

```sh
uv run python -m skill_exchange.cli publish-local --scanner fixture --fixture skillspector-clean.json
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
- `.exchange/generated/boe/` stores official local BOE records.
- `.exchange/generated/zips/` stores runtime skill zip downloads.

## Boundaries

The local mock does not implement GitLab API behavior, merge restrictions, approval rules, protected branches, or bot authentication. It exists to prove the exchange building blocks before real GitLab integration.
