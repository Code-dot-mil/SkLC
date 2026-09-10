# Static Skill Exchange Site Spec

Date: 2026-06-19

## Purpose

This repository implements a static skill exchange for publishing agent skills with visible scanner-backed risk context, reviewer assessment context, generated bill-of-evidence bundles, runtime zip downloads, and a GitLab Pages catalog.

The exchange starts as a GitLab repository plus a GitLab Pages static site. The repository is the source of truth for skill content and exchange policy. Python tooling validates skills, runs NVIDIA SkillSpector, generates official evidence, produces deploy-time data, and packages skill downloads. The Astro site renders the generated data into a searchable catalog and detail pages.

The design deliberately avoids a backend service, database, MCP endpoint, user account model, custom AI review workflow, executable eval harness, click tracking, view tracking, install tracking, and download tracking. CI is the publisher. The generated data contract and BOE layout are the migration path if a backend is added later.

## Goals

- Publish a searchable static skill catalog for authenticated organization users through GitLab Pages.
- Show plain-language use guidance for every displayed skill: `Safe to use`, `Use caution`, `Avoid installing`, or `Unknown`.
- Preserve the underlying scanner risk level for every displayed skill: `Low`, `Medium`, `High`, or `Unknown`.
- Use SkillSpector assessment output as the first scanner-backed consumer risk signal.
- Give human reviewers merge request assessment context before accepting new or changed skills.
- Produce official BOE only from protected publication CI, not from human-authored files.
- Reuse official BOE when the computed scan cache key already exists.
- Support both `static-only` and `llm-assisted` SkillSpector scans.
- Keep all environment-specific settings configurable through environment variables or GitLab CI variables.
- Keep the site and tooling self-contained so the repository can move between networks without importing external CI components.

## Non-Goals

- No live application server.
- No API, MCP surface, or dynamic exchange service.
- No metrics for views, clicks, installs, or downloads.
- No formal blocking gate based on SkillSpector findings in the MVP.
- No skill maturity field in the MVP.
- No executable skill evaluation harness or no-skill baseline comparison.
- No custom AI-backed reviewer.
- No protected-branch administration logic in application code.
- No GitLab API simulator in the current codebase.

## Repository Shape

The repository must have this shape:

```text
.exchange/
  categories.yaml
  display-policy.yaml
  risk-policy.yaml
  site-config.json
  tags.yaml
  generated/
    .gitkeep
    boe/
      <namespace>/
        <skill-id>/
          <content-hash>/
            <scan-cache-key>/
              boe.json
              hashes.json
              scanner-config.json
              skillspector.json
              summary.json

.skill-lifecycle/
  metadata/
    <skill-id>.yaml

contracts/
  README.md
  skill-package/v1/
  assessment-result/v1/
  boe/v1/
  catalog/v1/
  catalog-policy/v1/
  release-manifest/v1/

scripts/
  skill_exchange/
    __init__.py
    boe.py
    ci.py
    cli.py
    exchange_builder.py
    frontmatter.py
    models.py
    policy.py
    risk.py
    skills.py
    skillspector.py
    validation.py
    zipper.py

site/
  .npmrc
  astro.config.mjs
  package.json
  package-lock.json
  scripts/
    copy-downloads.mjs
  src/
    components/
      RecommendationBadge.astro
      ScannerFindings.tsx
      SkillCatalog.tsx
    layouts/
      BaseLayout.astro
    lib/
      exchange-data.mjs
      sanitize-skill-html.mjs
      url-state.d.ts
      url-state.mjs
    pages/
      index.astro
      skills/[namespace]/[skillId].astro
    styles/
      global.css
  tests/
    copy-downloads.test.mjs
    sanitize-skill-html.test.mjs
    url-state.test.mjs
  tsconfig.json

skills/
  <namespace>/
    <skill-id>/
      SKILL.md
      references/
      scripts/
      assets/

tests/
  fixtures/
    skills/
      ai4sdlc/
        sample-skill/
          SKILL.md
  test_build_exchange.py
  test_ci.py
  test_cli.py
  test_frontmatter.py
  test_risk.py
  test_skills.py
  test_skillspector.py
  test_validation.py
  test_zips.py

.gitignore
.gitlab-ci.yml
AGENTS.md
CI.md
CONTRIBUTING.md
GOVERNANCE.md
Justfile
README.md
package.json
pyproject.toml
uv.lock
uv.toml
```

Durable generated evidence is limited to `.exchange/generated/boe/`. Derived generated outputs such as `.exchange/generated/index.json`, `.exchange/generated/tables/`, `.exchange/generated/skills/`, `.exchange/generated/scanner-runs/`, `.exchange/generated/zips/`, `site/public/downloads/`, and `site/dist/` are deploy-time or local build artifacts and must not be committed.

### Cross-product contract sources

`contracts/` is a source-governance boundary for serialized formats shared by independently releasable products. It is not a runtime package or an additional product. It contains versioned schemas, examples, and explanatory contract documents only; it must not contain executable implementation, CI, deployment configuration, policy instances, or release assembly logic.

A contract belongs under `contracts/` only when at least two products must agree on its serialized representation. Each contract names a governing product, and product releases vendor the exact schemas they produce or consume so installed products do not depend on the repository's `contracts/` directory at runtime.

The checked-in `v1` contracts are a first-pass target boundary for the near-term product separation. The current publisher still emits and consumes the implemented `skill-exchange-boe/v0` and generated-data formats documented below; adding the contract sources does not claim that current runtime output already conforms to `v1`. Migration requires explicit implementation and tests.

Contract major versions change when a required field, field meaning, or serialized shape changes incompatibly. Current catalog materialization will support only its declared current BOE major version. Legacy BOE may remain tracked as historical evidence, but it is not eligible for the current catalog and its presence alone is not an error. Currently served skill content without matching BOE in the supported schema must be reassessed or excluded.

`.gitignore` must ignore `.exchange/generated/*` while re-including `.exchange/generated/.gitkeep` and `.exchange/generated/boe/**`. It must also ignore `.exchange/local-generated/`, site build output, Node dependencies, Python caches, `.uv-cache/`, `.venv/`, and bytecode.

## Stack

Use Python 3.12 for exchange tooling and CI helpers. Use `uv` for dependency management. Python runtime dependencies are intentionally small; `PyYAML` is required, and tests use `pytest` and `ruff`.

Use Astro with TypeScript for the static site, with React components only for client-side interactivity. The site depends on Astro, React, React DOM, `@astrojs/react`, `@astrojs/markdown-remark`, and TypeScript. Node.js 22 is the target runtime for site build and tests.

`uv.toml` sets `index-url = "https://pypi.org/simple"`. `site/.npmrc` sets `registry=https://registry.npmjs.org/` and `replace-registry-host=registry.npmjs.org`. These defaults keep lockfile resolution stable while still allowing CI images and network access to be configured outside the repository.

Root `package.json` only wraps site commands with `npm --prefix site`: `site:build`, `site:lint`, `site:test`, and `site:typecheck`. Site `package.json` scripts are `prebuild`, `build`, `dev`, `lint`, `test`, and `typecheck`.

Use `just` as the cross-stack developer wrapper:

```sh
just lint
just test
just build
just ci-local
```

Use Python and Node directly for targeted checks:

```sh
uv run --extra test ruff check scripts tests
uv run --extra test pytest
uv run python -m compileall scripts tests
npm --prefix site run lint
npm --prefix site run test
npm --prefix site run build
```

## Exchange Policy Files

`.exchange/categories.yaml` defines controlled category values:

```yaml
categories:
  - id: security
    label: Security
  - id: testing
    label: Testing
  - id: documentation
    label: Documentation
  - id: collaboration
    label: Collaboration
```

`.exchange/tags.yaml` defines controlled tags:

```yaml
tags:
  - code-review
  - python
  - security
  - unit-tests
  - documentation
  - pull-requests
  - scanner-demo
  - testing
  - skillspector
```

`.exchange/display-policy.yaml` controls index visibility and display:

```yaml
show_unknown_risk: false
show_confidence_flags: true
default_sort: name
```

`show_unknown_risk: false` means generated skills with `Unknown` risk are omitted from default site index data. The detail record may still be written to generated output. `show_unknown_risk: true` includes `Unknown` skills in the generated index.

`.exchange/risk-policy.yaml` documents the risk mapping:

```yaml
risk_levels:
  high:
    finding_severities: ["critical", "high"]
  medium:
    finding_severities: ["medium"]
  low:
    finding_severities: []
unknown_reasons:
  - no_official_boe
  - scanner_failed
  - model_unavailable
  - malformed_report
  - scan_key_mismatch
confidence_flags:
  static_only:
    - Low confidence
```

`.exchange/site-config.json` supplies source-link defaults:

```json
{
  "sourceRepositoryUrl": "https://example.invalid/skill-exchange-site",
  "sourceBranch": "main"
}
```

`SKILL_EXCHANGE_SOURCE_REPOSITORY_URL` and `SKILL_EXCHANGE_SOURCE_BRANCH` may override `site-config.json` at generation time.

`SKILL_EXCHANGE_SHOW_SOURCE_LINKS` controls whether the static site renders `View source` links at Astro build time. It defaults to `true`; set it to `false`, `0`, `no`, or `off` for a build that should omit those links. Invalid values must fail the build instead of falling back silently.

## Skill Package Format

Skill packages live at `skills/<namespace>/<skill-id>/`. The folder path is the authoritative identity source. Namespaces are open in the MVP and should be based on the publishing GitLab group, team, or organization. The current implementation treats namespace as one filesystem path segment. Do not store a URL as the namespace.

Each package must include `SKILL.md` with YAML frontmatter at the start of the file. Optional `references/`, `scripts/`, and `assets/` directories are included in hashes and runtime zips.

Optional seed lifecycle metadata may live under `.skill-lifecycle/metadata/<skill-id>.yaml` using the same stable skill ID as the runtime package. This metadata is governance and validation context, not runtime skill instruction context, and is not included in runtime zips.

MVP-0.2 lifecycle metadata includes `schema_version`, `skill_id`, `tier`, `owner`, `purpose`, `intended_users`, `use_context`, `positive_triggers`, `negative_triggers`, and `known_failure_cases`. The current exchange publisher does not enforce these files yet; they are repository-level authoring inputs for the lifecycle validation path.

Minimum frontmatter:

```yaml
---
name: sample-skill
description: Use when this skill is needed.
metadata:
  ai4sdlc.namespace: ai4sdlc
  ai4sdlc.category: testing
  ai4sdlc.tags: unit-tests,testing
  ai4sdlc.owner: team-or-person
  ai4sdlc.upstream_url: https://example.org/original/skill
---
```

Validation behavior:

| Field | Behavior |
|---|---|
| `name` | Required. Must equal the `<skill-id>` folder name. Mismatch is an error. |
| `description` | Required and must not be blank. Blank is an error. |
| `metadata.ai4sdlc.namespace` | Optional. Warn if present and different from the namespace folder. |
| `metadata.ai4sdlc.category` | Optional. Warn if not present in `.exchange/categories.yaml`. |
| `metadata.ai4sdlc.tags` | Optional. Accept comma-separated string or YAML list. Warn for unknown values. |
| `metadata.ai4sdlc.owner` | Optional. Missing owner creates metadata flag `missing_owner`. |
| `metadata.ai4sdlc.upstream_url` | Optional. Records provenance for copied, forked, mirrored, or adapted skills. |

Unknown category and tag values are warnings, not failures, in the MVP. Reviewers decide whether uncontrolled values should be accepted.

## Python Data Model

`scripts/skill_exchange/models.py` defines frozen dataclasses:

- `SkillMetadata`: `namespace`, `skill_id`, `name`, `description`, optional `category`, tuple `tags`, optional `owner`, optional `upstream_url`, raw frontmatter dict, and computed `display_id` of `<namespace>/<skill-id>`.
- `SkillPackage`: metadata, package path, `SKILL.md` path, and `content_hash`.
- `ValidationResult`: tuple `errors`, tuple `warnings`, tuple `metadata_flags`, and property `ok`.

Use dataclasses for the Python model rather than introducing a heavier schema framework.

## Frontmatter Parsing

`frontmatter.py` parses `SKILL.md` frontmatter:

- The file must start with `---\n`.
- The closing marker must be `\n---\n`.
- Parsed YAML must be a mapping.
- Return `(frontmatter, body)`.
- Raise `ValueError` when the block is missing, unterminated, or not a mapping.

## Skill Discovery, Hashing, And Package Safety

`skills.py` discovers skills with `skills_root.glob("*/*/SKILL.md")`, sorted by path. For each skill:

- `namespace` is the parent folder name under `skills/`.
- `skill_id` is the skill folder name.
- Metadata is extracted from frontmatter.
- Tags may be comma-separated string or YAML list.
- `content_hash` is a SHA-256 hash of all package files.

`package_files(skill_dir)` must:

- Recursively include only regular files under the skill directory.
- Sort paths deterministically.
- Reject symlinks with `ValueError`.
- Reject any individual file larger than 5 MiB.
- Reject packages containing more than 500 files.

`hash_skill_package(skill_dir)` must hash each file as:

1. POSIX relative path bytes.
2. A NUL byte.
3. File bytes.
4. A NUL byte.

This makes skill content hash independent of local checkout path and sensitive to both file names and file contents.

## Validation

`validation.py` validates one `SkillPackage` against loaded exchange policy:

- Error when `metadata.name != metadata.skill_id`.
- Error when `description` is blank.
- Warning when declared namespace is present and does not match the folder namespace.
- Warning for unknown category.
- Warning for each unknown tag.
- Metadata flag `missing_owner` when owner is absent.

Publication skips invalid skills before scanner execution, detail generation, zip generation, and index inclusion. Invalid skills are reported in `invalid_skills`.

## SkillSpector Integration

`skillspector.py` owns scanner execution and scanner environment mapping.

Binary resolution:

- If `SKILLSPECTOR_BIN` is set, expand it and require the path to exist.
- Otherwise use `shutil.which("skillspector")`.
- If neither is available, raise `FileNotFoundError`.
- Do not silently substitute another scanner or mock.

Execution:

```text
skillspector scan <skill-path> --format json --output <output-path>
```

Append `--no-llm` for `static-only` scans. Use the scanner output file as the success criterion: if the output JSON file exists, parse and return it even when the process exit code is nonzero. This is required because scanners may return a finding exit code while still producing a valid report. If no output file exists, raise `RuntimeError` with stderr, stdout, or the exit code.

Version detection:

- Prefer Python package metadata for `skillspector`.
- Otherwise run `skillspector --version`.
- Normalize leading `v` from versions such as `v2.1.5` to `2.1.5`.
- Use `unknown` only when no version can be determined.

Generic LLM environment mapping:

| Exchange variable | SkillSpector/OpenAI variable |
|---|---|
| `SKILL_EXCHANGE_LLM_API_KEY` | `OPENAI_API_KEY` |
| `SKILL_EXCHANGE_LLM_BASE_URL` | `OPENAI_BASE_URL` |
| `SKILL_EXCHANGE_LLM_MODEL` | `SKILLSPECTOR_MODEL` |
| `SKILL_EXCHANGE_LLM_PROVIDER` | `SKILLSPECTOR_PROVIDER` |

Set `SKILLSPECTOR_PROVIDER=openai` only when API key, base URL, or model is set and provider is otherwise absent. Existing scanner/provider environment variables win over exchange variables. Do not add organization-specific LLM variable names.

## Risk And Recommendation Mapping

`risk.py` maps SkillSpector JSON to exchange risk:

- If report metadata contains `scan_error`, return `Unknown` with reason `scanner_failed: <error>`.
- If `issues` is not a list or `risk_assessment` is not a mapping, return `Unknown` with reason `Scanner report did not match the expected SkillSpector shape.`
- If any issue severity is `critical` or `high`, or native `risk_assessment.severity` is `critical` or `high`, return `High`.
- Else if any issue severity is `medium`, or native `risk_assessment.severity` is `medium`, return `Medium`.
- Else return `Low`.
- Static-only reports where `metadata.llm_requested` is false include confidence flag `Low confidence`.

Generated records preserve supported SkillSpector recommendations and normalize unsupported or missing values to `Unknown`. `exchange_builder.recommendation_label()` maps:

| Native recommendation | Label |
|---|---|
| `SAFE` | `Safe to use` |
| `CAUTION` | `Use caution` |
| `DO_NOT_INSTALL` | `Avoid installing` |
| `BLOCK` | `Avoid installing` |
| `Unknown` | `Unknown` |

The UI leads with recommendation labels because users need direct usage guidance. Scanner risk remains visible as supporting evidence.

## Scan Cache Key

Publication must not rerun SkillSpector when official evidence already exists for the current scan key.

`exchange_builder.make_scan_key()` must include:

- namespace;
- skill ID;
- skill content hash;
- normalized SkillSpector version;
- scan mode: `static-only` or `llm-assisted`;
- scanner config label;
- 16-character SHA-256 prefix of the normalized scanner config JSON.

Static scan keys use label `no-llm`. LLM-assisted scan keys use `<provider>-<model>`, sanitized to `[A-Za-z0-9_.-]` with other characters replaced by `-`.

Scanner config JSON includes:

```json
{
  "native_output_format": "skillspector-json-v2",
  "scan_mode": "static-only"
}
```

For LLM-assisted scans it also includes:

```json
{
  "llm_provider": "<provider>",
  "llm_model": "<model>"
}
```

The cache key must differ when the model or scanner config differs. Versions with and without a leading `v` are considered equivalent when looking for existing tracked BOE, so older BOE produced with `skillspector-v2.1.5` can satisfy a normalized `skillspector-2.1.5` lookup if the BOE itself matches that candidate key.

## BOE Bundles

`boe.py` writes official evidence under:

```text
.exchange/generated/boe/<namespace>/<skill-id>/<content-hash>/<scan-cache-key>/
```

Each bundle contains:

- `boe.json`
- `skillspector.json`
- `summary.json`
- `scanner-config.json`
- `hashes.json`

`skillspector.json` is the raw native report copied from the scanner output path. `summary.json` contains `risk`, `risk_reason`, and `confidence_flags`. `scanner-config.json` contains the scan config used in cache-key computation. `hashes.json` contains SHA-256 hashes for `boe.json`, `scanner-config.json`, `skillspector.json`, and `summary.json`.

`boe.json` schema version is `skill-exchange-boe/v0` and includes:

- namespace, skill ID, display ID, skill path;
- source commit SHA;
- skill content hash;
- scan cache key;
- scanner name and version;
- scan mode;
- provider and model when applicable;
- scan timestamp and generated timestamp;
- CI pipeline ID and job ID when available;
- risk, risk reason, confidence flags;
- validation warnings and metadata flags;
- paths to native scanner output, summary, scanner config, hashes, and report source.

Human contributors must not hand-author BOE. Official BOE comes from protected publication CI.

## Exchange Builder

`exchange_builder.build_exchange()` is the core publisher. Inputs:

- `skills_root`
- `exchange_dir`
- `generated_dir`
- tuple `scan_modes`
- `reuse_boe_only`, default false

Behavior:

1. Create `generated_dir`.
2. Load exchange policy and site config.
3. Discover skill packages.
4. Read existing generated scanner tables when present.
5. Build an in-memory scanner cache by `scan_cache_key` using the latest `last_scanned`.
6. For each skill, validate metadata. If validation has errors, add display ID to `invalid_skills` and skip all outputs for that skill.
7. For each requested scan mode:
   - when `reuse_boe_only` is true, preflight exact-current-content tracked BOE for every valid skill and requested mode, require a complete symlink-free bundle with matching declared SHA-256 hashes, recomputed scan key, scanner version/mode, LLM provenance, a successful scanner report with the expected issue and risk-assessment shape and no error markers, and assessment fields consistent across the report, summary, and BOE, select the newest valid bundle deterministically by scan timestamp and scan cache key, and fail with the missing skill/mode list before writing derived output;
   - the reuse-only path obtains scanner version, configuration, report, and provenance from tracked BOE and never calls SkillSpector, computes a live scanner configuration, reads live LLM configuration, or writes BOE;
   - otherwise compute scanner version, scanner config, and scan cache key;
   - first reuse matching current scanner-run table entries when the native report still exists;
   - otherwise reuse matching tracked BOE bundles from `.exchange/generated/boe/`;
   - otherwise run SkillSpector;
   - if SkillSpector raises, synthesize a scanner failure report with metadata `scan_error`, write it to the temporary report path, and continue with `Unknown` risk;
   - write BOE;
   - mirror run artifacts into `.exchange/generated/scanner-runs/<run-id>/`;
   - append rows for scanner runs, scanner artifacts, and scanner findings.
8. Write a runtime skill zip to `.exchange/generated/zips/<namespace>--<skill-id>.zip`.
9. Write a skill detail JSON record under `.exchange/generated/skills/<namespace>--<skill-id>.json`.
10. Select the display assessment from the latest scanner run, using scan mode tie-breaker where `llm-assisted` outranks `static-only`.
11. Include the skill in `.exchange/generated/index.json` only when risk is not `Unknown` or `show_unknown_risk` is true.
12. Write table files under `.exchange/generated/tables/`.
13. Return JSON-compatible result with `skills_written`, `reused_scans`, and `invalid_skills`.

Generated skill records include:

- `namespace`, `skill_id`, `display_id`, `name`, `description`;
- `category`, `tags`, `owner`, `owner_missing`, `upstream_url`;
- `content_hash`;
- `skill_files` with relative path and byte size;
- raw `skill_md_content`;
- `source_path`, `source_url`;
- `last_updated`, `first_observed`, `latest_source_commit_sha`;
- `last_scanned`;
- `risk`, `risk_reason`;
- `recommendation`, `recommendation_label`;
- `confidence_flags`;
- selected `scan_mode` and all `scan_modes`;
- `scanner_provenance`;
- `scanner_run_ids`;
- canonical `boe_path`;
- `detail_path`, `zip_path`, `download_path`;
- validation warnings and metadata flags.

`last_updated`, `first_observed`, and `latest_source_commit_sha` should come from Git history for the skill path when available, with file mtimes as the local fallback for timestamps when not in a git checkout.

## Generated Tables

The builder writes JSON table files under `.exchange/generated/tables/`. Each table has schema version `skill-exchange-table/<name>/v0` and a `rows` array.

`skills.json` contains the full generated skill records, including records omitted from the public index when unknown risk is hidden.

`scanner_runs.json` rows include:

- run ID;
- scan cache key;
- skill identity;
- content hash;
- last scanned timestamp;
- scanner name `skillspector`;
- scanner type `security`;
- scanner version;
- scanner config hash;
- scan mode;
- LLM provider and model when applicable;
- native output format `skillspector-json-v2`;
- native report path, summary path, BOE path, canonical BOE path;
- status `completed` or `failed`;
- native score, native severity, native recommendation;
- display risk, display risk reason, confidence flags.

`scanner_artifacts.json` rows include one `native_report`, one `summary`, and one `boe` artifact per scanner run, each with a relative `downloads/scanner-runs/<run-id>/...` download path.

`scanner_findings.json` rows preserve native SkillSpector issue details:

- native issue ID;
- severity, category, pattern, confidence;
- file path and start/end line;
- explanation, remediation, code snippet;
- full native finding JSON.

## Runtime Zip Downloads

`zipper.py` writes one zip per skill package:

```text
.exchange/generated/zips/<namespace>--<skill-id>.zip
```

The archive must preserve the skill directory:

```text
<skill-id>/SKILL.md
<skill-id>/references/...
<skill-id>/scripts/...
<skill-id>/assets/...
```

Only files from the skill package are included. Exchange governance files, BOE, generated data, and repository tooling are not included. Zip creation uses `package_files()`, so symlinks and oversized packages are rejected consistently with hashing.

Each exchange build clears the generated `zips/` directory before packaging the current valid skill set, so archives from prior builds are not retained after a skill is removed or becomes invalid.

## Prebuilt Release Packaging

`scripts/skill_exchange/release.py` assembles the prebuilt site without invoking
Node, generating exchange data, assessing skills, or creating a standalone catalog.
Its `build` command takes `--version`, `--source-revision`, `--repo-root`,
`--site-dir` (default `site/dist` relative to the repository), and `--output-dir`.
The version must be SemVer without a leading `v`. `SOURCE_DATE_EPOCH`, when set,
controls the manifest timestamp and archive timestamps for repeatable builds.

The archive is named `deployment-kit-prebuilt-<version>.tar.gz` and has one
`deployment-kit-prebuilt-<version>/` root. Already-built site files go in `public/`;
`index.html`, `assets/`, and `downloads/` must exist. The site's root `.gitkeep`
is excluded. The builder copies the deployment CI from
`products/deployment-kit/ci/gitlab/prebuilt/.gitlab-ci.yml`, the README and three
installation/deployment guides from `products/deployment-kit/docs/prebuilt/`, and
the release-manifest schema from `contracts/release-manifest/v1/`. Missing required
inputs fail the build; the builder does not generate substitute documentation.

The package's manifest and checksums cover the same installation files, excluding
only their own two root metadata files. Nested assets with either metadata filename
are included. External `release-manifest.json` records only the prebuilt archive;
external `SHA256SUMS.txt` covers that archive and the external manifest. No catalog
archive or release-notes asset is produced by this builder.

The builder also vendors `products/deployment-kit/scripts/verify_prebuilt.py`
as `scripts/verify_prebuilt.py` and includes it in the manifest and checksums.
Installation and the deployment-only GitLab `pages` job invoke that same offline
Python 3.12+ script. It validates the vendored manifest schema (including date/time
and offset ranges), compares the manifest and checksum file sets, verifies file
digests and required files/directories, rejects links and escaping paths, and
scans static HTML attributes, JSON string values, and JavaScript string literals
for missing downloads. HTML entities and JSON/JavaScript escapes must be decoded;
download queries/fragments are ignored and URL-encoded traversal is rejected.
JavaScript scanning must keep regular-expression literals (including escaped
slashes and character classes) separate from quoted download strings and division
operators, so a pattern cannot hide a later missing download. Apply the same rule
to inline scripts and standalone JavaScript files; regex contents are not URLs.
Unknown schema features fail closed. All installation files must be recorded;
only root metadata and top-level `.git` checkout metadata are excluded. Verification
does not modify `public/`, and the job publishes that existing directory only
after success. The package can be copied into a differently named GitLab checkout;
`--expected-version` is available for matching the initially downloaded archive.

### Input safety

Prebuilt release staging helpers live in `scripts/skill_exchange/release.py`.
Before copying a source tree, they must reject symbolic links and Windows directory
junctions at the source root, in its parent path, and anywhere inside the tree.
Single-file inputs must reject linked files and linked parent directories as well.
Source paths must be checked before resolving links or traversing directories.
Tree validation must finish before creating or copying destination contents, so a
rejected source leaves no partially copied tree. Ordinary files, nested directories,
and empty directories must be preserved in the trusted package staging directory.
The source tree must remain unchanged during validation and copying.

## Local CLI

`cli.py` provides local publication:

```sh
uv run python -m skill_exchange.cli publish-local --generated-dir .exchange/local-generated --scan-mode static-only
```

`--scan-mode` may be repeated. If omitted, local publication runs both `static-only` and `llm-assisted`. The `Justfile` should call local generation with `.exchange/local-generated/` and default to `static-only` so developers do not rewrite tracked CI BOE for convenience.

`--reuse-boe-only` reconstructs disposable index, table, scanner-run, detail, and zip output from tracked BOE for exact current skill content. It fails when any requested skill/mode lacks valid tracked evidence and when the resulting public index is empty. This mode cannot run SkillSpector or an LLM.

## CI Helper CLI

`ci.py` provides GitLab-focused commands:

```sh
uv run python -m skill_exchange.ci review --artifacts-dir review-artifacts
uv run python -m skill_exchange.ci publish --result-path publish-result.json
```

Supported scan modes are `static-only` and `llm-assisted`. `parse_scan_modes()` accepts comma-separated and whitespace-separated values.

### Review Command

The review command:

- resolves base ref from explicit args, `SKILL_EXCHANGE_DIFF_BASE`, `CI_MERGE_REQUEST_DIFF_BASE_SHA`, or merge-base with the target/default branch;
- resolves head ref from explicit args, `SKILL_EXCHANGE_DIFF_HEAD`, `CI_COMMIT_SHA`, or `HEAD`;
- detects changed skill package roots from `git diff --name-only --diff-filter=ACMRT <base> <head> -- skills`;
- validates only changed skill package roots;
- runs SkillSpector for each changed valid skill;
- writes `review-artifacts/validation.json`;
- writes `review-artifacts/changed-skills.json`;
- writes `review-artifacts/comment.md`;
- writes `review-artifacts/result.json`;
- optionally posts a merge request comment.

Review validation errors fail the job when `SKILL_EXCHANGE_REVIEW_FAIL_ON_VALIDATION_ERRORS` is true. Scanner errors fail the job only when `SKILL_EXCHANGE_REVIEW_FAIL_ON_SCANNER_ERROR` is true. Scanner failure otherwise appears as `Unknown` review context.

The review comment must include:

- top table with skill, risk, flags, scan mode, and reason;
- `Scanner findings` section;
- every scanner finding with severity, issue ID, category/pattern title, location, confidence, finding text, explanation, remediation, and code snippet;
- `Exchange validation` section listing errors, warnings, and metadata flags.

Merge request comments use:

- `SKILL_EXCHANGE_POST_REVIEW_COMMENT` to enable posting;
- `SKILL_EXCHANGE_REVIEW_TOKEN_VARIABLE` to name the token variable, default `GITLAB_TOKEN`;
- `SKILL_EXCHANGE_REVIEW_TOKEN_HEADER` to override the header, otherwise `JOB-TOKEN` for `CI_JOB_TOKEN` or `PRIVATE-TOKEN` for other token variables.

Posting targets:

```text
POST <CI_API_V4_URL>/projects/<CI_PROJECT_ID>/merge_requests/<CI_MERGE_REQUEST_IID>/notes
```

### Publish Command

The publish command runs `build_exchange()`, writes the result JSON, and optionally commits generated BOE.

When `--commit-generated` or `EXCHANGE_PUBLISH_COMMIT=true` is set, `commit_generated_outputs()` must:

- commit only `.exchange/generated/boe/`;
- use `git add -f -- .exchange/generated/boe`;
- not add derived `index.json`, `tables/`, `skills/`, `scanner-runs/`, or `zips/`;
- return `no BOE generated` when no BOE directory exists;
- return `no generated changes` when staged BOE is unchanged;
- use conventional default commit message `chore: update generated exchange evidence`;
- push to `EXCHANGE_PUBLISH_BRANCH` or `CI_DEFAULT_BRANCH` when `EXCHANGE_PUBLISH_PUSH` is true.

Publish authentication must keep review credentials separate from publication credentials. Push remote configuration order:

1. Use `EXCHANGE_PUBLISH_PUSH_URL` when provided.
2. Else use `EXCHANGE_PUBLISH_TOKEN` with `EXCHANGE_PUBLISH_USERNAME` or username `oauth2`.
3. Else use `CI_JOB_TOKEN` with username `gitlab-ci-token`.
4. Else fail with an explicit error explaining required publication variables.

Do not use `GITLAB_TOKEN` as an implicit publication fallback. That token may be a review/comment token with insufficient protected-branch permissions. Silent credential substitution hides defects.

## GitHub Validation

The repository owns `.github/workflows/ci.yml`. The workflow runs on every pull request targeting `main` and every push to `main` using GitHub-hosted Ubuntu runners.

Python 3.12 jobs run `uv run --extra test ruff check scripts tests` and `uv run --extra test pytest`. Node.js 22 jobs run `npm --prefix site run lint` and `npm --prefix site run test` after `npm ci --prefix site`. Each command is a blocking check. A separate Python 3.12 producer fetches full Git history, sets source repository and immutable commit context from the pull-request head or push, and uses reuse-BOE-only mode to create non-empty derived exchange data. Reused BOE must represent a successful scan with the expected report shape and internally consistent assessment fields. The producer uploads the derived data for a Node.js 22 consumer. The consumer waits for validation and builds `site/dist/`.

The artifact job must package the built site with `skill_exchange.release build`
under Python 3.12, extract the archive, and run its included
`scripts/verify_prebuilt.py` with the expected version before upload. Preserve
checks for a nonempty home page, catalog detail pages, skill ZIP downloads, and
the absence of the site's root `.gitkeep`. Use a fresh staging directory under
`RUNNER_TEMP`. Only after all checks succeed may the complete extracted package
root be uploaded as `static-site`, including hidden deployment files. The ZIP
must contain `public/`, docs, the deployment CI, vendored schema, verifier,
manifest, and checksums at their customer installation paths, not bare site
output or a nested tar archive.

CI versions are `0.0.0-ci.<run-id>.<run-attempt>` and do not select a product
release version. The manifest source revision is `github.sha`, which identifies
the checked-out PR merge commit or push commit. This validation job creates no
tag or GitHub Release. Regression tests must execute the workflow's packaging
commands against already-built fixture content, verify the configured upload
layout after ZIP extraction, and prove invalid download references stop the job.

## GitHub Release Automation

`.github/workflows/release.yml` implements the manual-tag path from
`docs/specs/release-process.md` for `deployment-kit-prebuilt` only. It runs on
`v*.*.*` tag pushes, validates the version as SemVer without its leading `v`, and
requires the checkout to match the tag's commit. It neither chooses a release
version nor creates a tag. Maintainers must complete the release checklist first.

`RELEASE_NOTES.md` stores accepted sections headed `## <version>`. The
`skill_exchange.release release-notes` command must extract exactly that section,
including its heading and subsections, without adjacent releases. Ignore fenced
code examples when finding headings. Missing, duplicate, empty, or linked notes
inputs fail. `validate-version` exposes the builder's existing version validation.
The workflow reads committed, unmodified notes from the tagged checkout before
build steps and uses the extracted snippet as the GitHub Release description.

Python 3.12 and Node.js 22 run repository checks, reuse-only exchange generation,
and the site build. No scanner or LLM may run. The release uses the same builder
and included verifier as CI, with extraction, expected-version checking, required
site-content checks, and external checksum verification before publication. Build
metadata records the tag's commit, with `SOURCE_DATE_EPOCH` from that commit.

Use a fresh directory under `RUNNER_TEMP`. Publish exactly
`deployment-kit-prebuilt-<version>.tar.gz`, `release-manifest.json`, and
`SHA256SUMS.txt` via `gh release create --verify-tag --notes-file ...`. No catalog
archive or release-notes asset is uploaded. Existing releases must not be
overwritten. SemVer prereleases are marked as GitHub prereleases. Keep the release
token scoped to the publishing step, disable persisted checkout credentials, and
use a 30-minute GitHub-hosted job with non-cancelling per-tag concurrency.

## GitLab CI

The repository owns `.gitlab-ci.yml` directly. Do not import external CI components.

Stages:

```yaml
stages:
  - lint
  - test
  - audit
  - review
  - publish
  - deploy
```

Workflow creates pipelines for schedules, merge requests, default-branch commits, and tags.

Global CI defaults:

- `GIT_DEPTH: "0"` so git history is available for timestamps and diffs.
- Python image defaults to `docker.io/library/python:3.12-bookworm`.
- Node image defaults to `docker.io/library/node:22-bookworm-slim`.
- `PYTHON_BOOTSTRAP_COMMAND` defaults to installing `uv`.
- `SKILL_EXCHANGE_RUNNER_TAG` and `PAGES_RUNNER_TAG` route jobs without hardcoding one environment's runner setup.
- `SKILLSPECTOR_INSTALL_COMMAND` defaults empty and may install SkillSpector at runtime.
- Review scan mode defaults `static-only`.
- Publish scan modes default `static-only`.
- Review comments default disabled.
- Publish commits default disabled globally but enabled in `publish:exchange`.

Path rules:

- `lint`, `test`, and `audit` run only when site code, exchange tooling, tests, policy, lockfiles, or CI configuration changes.
- `review:skills` runs only for merge requests with `skills/**/*` changes.
- `publish:exchange` runs on schedules and default-branch push pipelines with `skills/**/*` changes.
- `generate:exchange` runs on default-branch push pipelines that do not change skills.
- `pages` runs on schedules and default-branch push pipelines and consumes artifacts from `publish:exchange` or `generate:exchange`.

Python jobs:

- run in `$PYTHON_IMAGE`;
- use `$SKILL_EXCHANGE_RUNNER_TAG`;
- run `uv sync --extra test`;
- cache `.uv-cache/`.

Node jobs:

- run in `$NODE_IMAGE`;
- use `$SKILL_EXCHANGE_RUNNER_TAG` except `pages`;
- run `npm ci --prefix site --cache "$NPM_CACHE_DIR" --prefer-offline`;
- cache `.npm/`.

Jobs:

- `lint:python`: `ruff check`, `compileall`, and YAML parse for `.gitlab-ci.yml`.
- `lint:site`: `npm --prefix site run lint`.
- `test:python`: `uv run pytest`.
- `test:site`: `npm --prefix site run test`.
- `audit:python`: configurable `PYTHON_AUDIT_COMMAND`.
- `audit:site`: `npm audit --prefix site --audit-level "$NPM_AUDIT_LEVEL"`.
- `review:skills`: installs or locates SkillSpector, runs CI review, stores `review-artifacts/`.
- `publish:exchange`: installs or locates SkillSpector, runs CI publish, stores `.exchange/generated/` and result JSON.
- `generate:exchange`: same as publish but without committing BOE.
- `pages`: builds the site, replaces top-level `public/` with `site/dist`, and publishes `public/`.

`pages` must be named exactly `pages` and publish a top-level `public/` artifact for GitLab Pages.

Merges to the default branch that change skills must run `publish:exchange` before `pages` so the first deploy of changed skills uses committed BOE instead of waiting for scheduled backfill.

## Dependency Vulnerability Management

GitHub Dependabot is the authoritative dependency-vulnerability control. Repository settings must enable Dependabot alerts and Dependabot security updates. Alert triage occurs only in GitHub Security; scheduled CI must not create a duplicate issue backlog.

The Dependabot configuration must cover the root Python `pyproject.toml` and `uv.lock` through the `uv` ecosystem and the Node `site/package.json` and `site/package-lock.json` through the `npm` ecosystem. Version updates run weekly on Monday. Minor and patch updates are grouped per ecosystem, major updates remain separate, default dependency and ecosystem labels are used, and pull requests are assigned to `Fnorgh2`.

`Fnorgh2` owns alert triage and notifications for high- and critical-severity alerts. High and critical alerts are reviewed when received, the remaining backlog is reviewed weekly, and unresolved alerts are escalated to repository administrator `scotluns`. The legacy `.gitlab-ci.yml` is not an active dependency-vulnerability control for this GitHub repository.

## CI Configuration And Permissions

All environment-specific values must be configured through generic CI variables. Do not add organization-specific variable names, registry names, credentials, or provider names.

Important variables:

- `PYTHON_IMAGE_REGISTRY`, `PYTHON_IMAGE_REPOSITORY`, `PYTHON_IMAGE_TAG`, `PYTHON_IMAGE`;
- `PYTHON_BOOTSTRAP_COMMAND`;
- `NODE_IMAGE_REGISTRY`, `NODE_IMAGE_REPOSITORY`, `NODE_IMAGE_TAG`, `NODE_IMAGE`;
- `SKILL_EXCHANGE_RUNNER_TAG`;
- `PAGES_RUNNER_TAG`;
- `SKILLSPECTOR_INSTALL_COMMAND`;
- `SKILLSPECTOR_BIN`;
- `SKILL_EXCHANGE_REVIEW_SCAN_MODE`;
- `SKILL_EXCHANGE_REVIEW_FAIL_ON_VALIDATION_ERRORS`;
- `SKILL_EXCHANGE_REVIEW_FAIL_ON_SCANNER_ERROR`;
- `SKILL_EXCHANGE_POST_REVIEW_COMMENT`;
- `SKILL_EXCHANGE_REVIEW_TOKEN_VARIABLE`;
- `SKILL_EXCHANGE_REVIEW_TOKEN_HEADER`;
- `SKILL_EXCHANGE_PUBLISH_SCAN_MODES`;
- `SKILL_EXCHANGE_LLM_API_KEY`;
- `SKILL_EXCHANGE_LLM_BASE_URL`;
- `SKILL_EXCHANGE_LLM_MODEL`;
- `SKILL_EXCHANGE_LLM_PROVIDER`;
- `EXCHANGE_PUBLISH_COMMIT`;
- `EXCHANGE_PUBLISH_PUSH`;
- `EXCHANGE_PUBLISH_BRANCH`;
- `EXCHANGE_PUBLISH_PUSH_URL`;
- `EXCHANGE_PUBLISH_TOKEN`;
- `EXCHANGE_PUBLISH_USERNAME`;
- `EXCHANGE_BOT_GIT_NAME`;
- `EXCHANGE_BOT_GIT_EMAIL`;
- `EXCHANGE_PUBLISH_COMMIT_MESSAGE`.

Review token and publish token paths are intentionally separate. Review credentials post optional MR notes. Publish credentials push BOE to the protected default branch. If GitLab job-token repository push is enabled, publication may use `CI_JOB_TOKEN` with username `gitlab-ci-token`; otherwise configure a masked `EXCHANGE_PUBLISH_TOKEN` for a publisher identity allowed to push to the protected default branch.

Schedule variables override project variables. Avoid duplicating project-level CI variables on a schedule unless the schedule intentionally needs a different value, especially `SKILL_EXCHANGE_PUBLISH_SCAN_MODES`.

## Site Data Loading

`site/src/lib/exchange-data.mjs` reads generated JSON from:

- `SKILL_EXCHANGE_GENERATED_ROOT`, when set;
- otherwise `<repository-root>/.exchange/generated`.

The repository root defaults to `SKILL_EXCHANGE_REPOSITORY_ROOT` or the parent directory of the site working directory.

Read:

- `index.json`, defaulting to `{ skills: [] }` when absent;
- `tables/scanner_runs.json`, defaulting to `{ rows: [] }`;
- `tables/scanner_findings.json`, defaulting to `{ rows: [] }`;
- `tables/scanner_artifacts.json`, defaulting to `{ rows: [] }`.

The empty fallback is explicit to allow a valid empty catalog build before generated data exists.

## Portable Site Paths

The same static output must work at a host root or beneath a project path without
rebuilding it for that destination. Astro emits bundled CSS and JavaScript into
`assets/` with the relative asset prefix `.`. Keep directory-format page output.

`BaseLayout` sets a relative HTML base using `relativeSiteRoot(Astro.url.pathname)`:
`./` for the catalog and `../../../` for a skill detail page. Catalog links,
back links, skill ZIP downloads, and scanner-evidence downloads resolve against
that site root. Generated download URLs begin with `downloads/`, never `/downloads/`.
External source and documentation URLs remain unchanged.

Node tests must build the actual site templates with fixture data and check that
navigation, download, stylesheet, and client-module URLs serve successfully from
the same output at both root and nested hosting paths. Python tests verify the
relative download URLs produced in the index, detail records, and tables.

## Site UX

The first page is the usable catalog, not a marketing landing page.

`site/src/pages/index.astro`:

- uses `BaseLayout`;
- shows header eyebrow `Agent skill catalog`;
- uses H1 `Skill Exchange`;
- states that users can browse scanner-assessed, evidence-backed skill packages;
- includes an external link to the agentskills.io open standard with no referrer;
- loads `SkillCatalog` with generated skills.

`SkillCatalog.tsx`:

- supports text search across display ID, name, description, category, and tags;
- filters by recommendation: all, `DO_NOT_INSTALL`, `CAUTION`, `SAFE`, `Unknown`;
- filters by category, treating absent category as `uncategorized`;
- sorts by name, recommendation, last updated, or last scanned;
- persists query state with URL params `q`, `recommendation`, `category`, and `sort`;
- removes default values from the URL and preserves unrelated params;
- renders cards with recommendation pills, confidence flags, category, description, tags, risk, last scanned, owner, scanner, and a detail link.

Recommendation sort ranks `DO_NOT_INSTALL` as 3, `CAUTION` as 2, `SAFE` as 1, and `Unknown` as 0. Unranked values use the default rank 0.

`site/src/pages/skills/[namespace]/[skillId].astro`:

- generates static paths from the public index;
- shows a back link to catalog;
- leads with skill display ID, description, recommendation, download action, and optional source link controlled by `SKILL_EXCHANGE_SHOW_SOURCE_LINKS`;
- shows a trust snapshot with use guidance, scanner risk, scanner, scan mode, last scanned, and owner;
- includes a recommendation info dialog explaining scanner-derived recommendation and risk basis;
- shows last updated, first observed, and optional upstream source;
- provides top-level tabs for `Skill Instructions` and `Assessment Evidence`;
- within `Skill Instructions`, provides tabs for rendered instructions and package file list;
- renders frontmatter rows before skill Markdown content;
- in `Assessment Evidence`, shows summary, content hash, and `ScannerFindings`;
- persists detail tab state with URL params `tab` and `fileTab`.

`ScannerFindings.tsx`:

- sorts scanner runs newest first;
- defaults to latest run;
- supports URL params `run`, `runs`, and `severity`;
- can show latest only or all older runs;
- renders scanner, date, mode, content hash, native severity, native score, display risk, finding count, and evidence download link;
- supports selecting a run and filtering findings by severity;
- exposes a scanner-runs info dialog;
- shows finding cards with native issue ID, category, severity, pattern, explanation, location, code snippet, and remediation.

`RecommendationBadge.astro` renders recommendation and confidence flags. `global.css` supplies a polished operational dark theme with high-contrast cards, controls, tables, dialogs, tabs, chips, responsive grids, and accessible focus states.

## Site Markdown Safety

Skill Markdown is content authored by contributors. The detail page must not allow contributor HTML to execute.

Rendering rules:

- Use Astro's Markdown processor to render the body after frontmatter parsing.
- Replace Markdown links with inert spans during rendering so links in skill instructions do not become active site links.
- Sanitize rendered HTML with `sanitizeSkillHtml()`.

The sanitizer removes:

- `<script>`, `<style>`, `<iframe>`, `<object>`, `<embed>`, `<svg>`, and `<math>` elements, including self-closing forms;
- event-handler attributes like `onclick` and `onerror`;
- `href` or `src` attributes starting with `javascript:` or `data:text/html`.

Keep useful Markdown rendering such as headings, paragraphs, tables, code, and lists.

## Site Download Copying

`site/scripts/copy-downloads.mjs` runs as `prebuild`.

It must:

- clear and recreate `site/public/downloads/`;
- copy skill zip files from `.exchange/generated/zips/` to `site/public/downloads/`;
- read `.exchange/generated/tables/scanner_artifacts.json`;
- copy scanner artifacts from `.exchange/generated/scanner-runs/` to their declared download paths;
- reject artifact sources outside `.exchange/generated/scanner-runs/`;
- reject destinations outside `site/public/downloads/`;
- realpath-check existing sources to prevent symlink escape;
- support rebasing absolute artifact paths from a previous checkout by recognizing the `.exchange/generated/scanner-runs/` suffix.

## URL State

`site/src/lib/url-state.mjs` provides:

- `readQueryValue(search, key, fallback, allowedValues)`;
- `updateQueryString(search, updates, defaults)`;
- `replaceQueryState(updates, defaults, win)`.

Unsupported values must fall back to defaults. Default values must be removed from the query string. Unrelated query params must be preserved.

## Governance

Roles:

| Role | Responsibilities |
|---|---|
| Contributor | Proposes new or changed skills by merge request and responds to review feedback. |
| Skill owner | Optional in the MVP. Accountable for declared skill purpose, usefulness, and maintenance. |
| Reviewer | Reviews skill content, metadata, validation warnings, and SkillSpector context. |
| Maintainer | Owns merge authority and protects governance files, CI configuration, exchange policy, and publication rules. |
| Exchange bot | Runs protected publication, produces official BOE, commits BOE evidence, and publishes Pages output. |

Human workflow:

1. Contributor opens an MR with a new or changed skill.
2. MR CI validates package structure and metadata.
3. MR CI warns on unknown categories and tags.
4. MR CI runs SkillSpector when feasible.
5. MR CI writes artifacts and may post a reviewer-facing comment.
6. At least one human reviewer inspects the diff and assessment context.
7. Maintainer merges after required human approvals.
8. Default-branch skill changes or scheduled publication produce or reuse official BOE.
9. Publication commits BOE bundles under `.exchange/generated/boe/` when configured.
10. GitLab Pages publishes from generated artifacts.

Human contributors never author official BOE. MR SkillSpector output is advisory. Official BOE comes from protected publication CI.

Generated-output MRs from the exchange bot may be exempt from human review only when the diff is limited to generated BOE bundles under `.exchange/generated/boe/`. Human-authored MRs must never automerge under this rule. Any MR that changes source code, skill instructions, CI, policy, config, permissions, documentation, or governance files requires human review.

## Seed Skills

The repository includes seed skills under `skills/ai4sdlc/`, including:

- `benign-scanner-demo`;
- `code-change-description`;
- `inline-documentation`;
- `python-secure-code-review`;
- `unit-test-generation`.

Seed skills are exchange content and must follow the same metadata, review, scanner, and BOE rules as any contributed skill.

Scanner findings in seed skills should be addressed by improving skill wording when they are phrase-triggered false positives. Do not suppress scanner output without a recorded triage/waiver model; suppression support is out of scope for the MVP.

## Documentation

Repository documentation must stay aligned with this spec:

- `README.md` explains what the exchange is, how it works, setup, local workflow, CI workflow, configuration, and boundaries.
- `CI.md` documents pipeline behavior, schedules, publish authentication, and configurable variables.
- `GOVERNANCE.md` documents trust boundary, roles, human skill workflow, generated-output workflow, and MVP boundaries.
- `CONTRIBUTING.md` documents developer setup, local checks, Python tooling, site tooling, CI changes, generated files, documentation rules, and merge expectations.
- `AGENTS.md` documents agent-specific working rules, including generated-output boundaries, no silent fallbacks, test boundaries, and spec maintenance.

Documentation must not reveal local checkout paths, local machine state, secrets, personal tokens, or environment-specific provider names.

## No Silent Fallbacks

Do not add silent fallback behavior anywhere in the codebase. Hidden substitution masks defects. If fallback behavior is necessary, it must be explicit in code, documented, tested, and fail closed when no valid value exists.

Examples:

- Do not use a review/comment token as a publish credential when a publish token is absent.
- Do not swap scanners or scanner modes when SkillSpector is unavailable.
- Do not replace missing generated BOE with unofficial human-authored evidence.
- Do not hardcode environment-specific registries, providers, endpoints, runner tags, or credentials.

The few intentional fallback behaviors in this spec are explicitly documented and tested, such as empty site data for initial empty builds, git timestamp fallback to mtimes outside a checkout, and `CI_JOB_TOKEN` publication only when no explicit publish token is configured.

## Tests

Python tests must cover:

- frontmatter parsing and rejection;
- namespaced skill discovery;
- metadata validation errors, warnings, and missing owner flag;
- risk mapping for static low, medium, high, malformed, and scanner-failure reports;
- SkillSpector output-file success despite finding exit code;
- SkillSpector failure without report;
- SkillSpector version normalization;
- generic LLM environment mapping;
- absence of legacy organization-specific LLM variable names in key docs/code;
- exchange build writing index, BOE, zip, tables, recommendation, risk, provenance, source URL, timestamps, and content hash;
- invalid metadata blocking publication output;
- scanner failure becoming `Unknown` when display policy allows unknowns;
- cache reuse from current generated scanner tables;
- cache reuse from tracked BOE when derived outputs are absent;
- reuse-BOE-only generation selecting current-content evidence without entering scanner, scanner-version, scanner-config, or LLM paths;
- reuse-BOE-only generation failing when requested current-content BOE is missing;
- scan cache key differences across mode/model/config;
- scanner finding row preservation;
- aggregation preferring latest run with LLM-assisted tie-break;
- supported recommendation normalization and plain-language labels;
- changed skill path detection;
- review artifact writing;
- review comment inclusion of every scanner finding;
- scan-mode parser;
- BOE-only generated commit behavior;
- publish authentication using `CI_JOB_TOKEN` when no publish token is configured;
- publish authentication not reusing review token;
- zip layout and symlink rejection;
- local CLI generated-dir handling.

Node tests must cover:

- recommendation option and query-state read/update behavior;
- skill Markdown sanitizer removing executable HTML;
- copy-downloads source containment, destination containment, and rebasing absolute generated artifact paths from another checkout.

Do not add placeholder tests that only lock command strings or package script spelling. Tests must prove behavior.

## Growth Path

Step 1 is this repository: static exchange with bot-controlled validation, visible risk/use guidance, official BOE, zip downloads, and GitLab Pages.

Step 2 can enrich the static exchange with better search, controlled filters, category/tag governance reports, richer detail pages, deprecation indicators, and clearer risk explanations.

Step 3 can add stronger lifecycle evidence such as owner signoff, intended use, trigger cases, non-trigger cases, known failure cases, and lightweight evaluation contracts. Model-assisted review remains advisory until enough output exists to define reliable blocking rules.

Step 4 can introduce a backend only when static hosting cannot meet user needs. A backend should ingest `.exchange/generated/index.json`, generated tables, and BOE bundles rather than replace them. Candidate backend capabilities include API, MCP, authenticated download policy, metrics, subscriptions, richer approval dashboards, and cross-repository aggregation.

The static data contract is the migration path. A backend becomes a query and workflow layer over the same bot-produced evidence.
