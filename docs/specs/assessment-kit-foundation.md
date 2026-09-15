# Assessment Kit Foundation Spec

## Decision baseline

This spec follows `docs/decisions.md`: the assessment kit is a standalone GitHub release that customers can install and run in GitLab without catalog or deployment dependencies.

## Milestone

`docs/roadmap.md` section 3.4, Assessment kit foundation.

## Status

Approved.

## Outcome

A customer installs the released assessment kit and assesses arbitrary skill packages, retaining native assessor output and BOE manifests.

## Release artifact

GitHub Releases publish:

- `assessment-kit-<version>.tar.gz`.
- External `assessment-kit-<version>.release-manifest.json` using
  `skill-exchange-release-manifest/v1`.
- External `assessment-kit-<version>.SHA256SUMS.txt` with SHA-256 entries for
  the archive and external manifest.

The archive also contains internal copies of `release-manifest.json` and
`SHA256SUMS.txt`. The external release manifest is authoritative metadata before
extraction. After extraction, the internal manifest must be byte-for-byte
identical to the external manifest.

The release manifest's `artifacts[]` records every extracted archive file except
`release-manifest.json` and `SHA256SUMS.txt`; it never records the containing
archive. This avoids a self-referential archive digest and gives the internal
and external manifest copies one meaning. The internal `SHA256SUMS.txt` is
`sha256sum` compatible and records the same extracted files and digests as
`artifacts[]`. The external `assessment-kit-<version>.SHA256SUMS.txt` records
`assessment-kit-<version>.tar.gz` and
`assessment-kit-<version>.release-manifest.json`, so a customer verifies the
archive before extraction and the installed files after extraction.

The archive expands to:

```text
assessment-kit-<version>/
  README.md
  release-manifest.json
  SHA256SUMS.txt
  dist/
    skill_assessment-<python-normalized-version>-py3-none-any.whl
  contracts/
    skill-package/v1/
    boe/v1/
    assessment-artifacts/v1/
    release-manifest/v1/
  docs/
    install.md
    commands.md
    assessor-configuration.md
    generated-files.md
```

For stable releases, `<python-normalized-version>` equals `<version>`. Python
package tooling may normalize a SemVer prerelease or build suffix, such as
`1.2.3-rc.1` to `1.2.3rc1`. The release manifest keeps the accepted SkLC
SemVer in `version` and records the installed Python version under
`components.skill-assessment`. Release assembly must verify that the two forms
are semantically equivalent and that the wheel filename matches its embedded
package metadata. Version comparison must preserve numeric component boundaries,
prerelease identity, and local/build components using Python packaging version
semantics; removing punctuation is not sufficient. A SemVer prerelease must
map to a Python prerelease; numeric or post-release spellings that Python would
interpret as a post-release are rejected. The manifest timestamp must
satisfy RFC 3339 date-time syntax, calendar validity, and timezone ranges.

`README.md` or `docs/assessor-configuration.md` must include a
`Dependencies` or `Prerequisites` section. For the first release it states that
SkillSpector is the only supported assessor, must be available on `PATH` or
through a documented `SKILLSPECTOR_BIN` setting, and must produce its normal
JSON report for the selected scan mode. An absent `SKILLSPECTOR_BIN` selects `PATH`; an explicit
blank value is invalid. The release documentation records the
exact supported SkillSpector version or source revision; a different version is
unsupported until compatibility tests approve it.
`docs/assessor-configuration.md` must document the assessment-kit `--config`
format, supported keys, defaults, environment-variable precedence, and
copy/paste-safe examples for the default `llm-assisted` path and explicit
`static-only` path. Installation documentation must show a local workflow that
verifies `SHA256SUMS.txt`, installs the wheel, satisfies the documented
SkillSpector prerequisite, configures the assessment kit, and confirms
`skill-assessment --help` works. Offline and air-gapped dependency delivery are
outside this milestone.

`docs/commands.md` must explain how to choose `--skill` versus `--root`. It must
state that `--root` points to a directory containing one or more unpacked skill
package directories beneath it, where each package directory contains its own
`SKILL.md`; the root itself does not need to be a skill package. The docs must
include a valid example tree and matching copy/paste-safe commands for
`validate`, `advise`, and `assess`.

`docs/generated-files.md` must document the exact output directory shapes for
`advise --output <directory>` and `assess --boe-root <directory>`, including
which paths are native assessor output, which paths are generated BOE metadata,
which output directory is safe to retain as an artifact, and how those shapes
map to the assessment-artifacts v1 contract.

## Public commands

All commands are exposed through the installed `skill-assessment` executable. Paths are filesystem paths in the current GitLab job or developer shell. Commands do not call GitHub, GitLab, Git, catalog tooling, site tooling, deployment tooling, or source-control write operations.

```text
skill-assessment validate (--skill <path> [--skill <path> ...] | --root <path>)
```

`validate` validates selected unpacked skill packages against `skill-package/v1`. A skill package is identified by the package directory name; `SKILL.md` frontmatter `name` must match that directory-derived name. Validation fails for unreadable paths, missing `SKILL.md`, invalid frontmatter, schema violations, symbolic links, paths escaping the skill directory, or duplicate selected skill names. It produces diagnostics only and writes no assessment output or BOE.

```text
skill-assessment advise (--skill <path> [--skill <path> ...] | --root <path>) \
  --assessor <id> [--assessor <id> ...] \
  --output <directory> \
  [--config <path>]
```

`advise` produces native assessor reports and author-facing `advice.md` without creating BOE, changing catalog policy, or making publication decisions. Exactly one selection mode is required: repeated `--skill` arguments or one `--root`. `--root` recursively selects every valid skill package below the supplied directory without requiring a namespace layout. At least one explicit `--assessor` is required; there is no default assessor. `--output` is the only write location for advice artifacts.

```text
skill-assessment assess (--skill <path> [--skill <path> ...] | --root <path>) \
  --assessor <id> [--assessor <id> ...] \
  --boe-root <directory> \
  [--config <path>]
```

`assess` is the formal evidence command. It runs each selected skill against each selected assessor, retains the assessor's native report bytes unchanged, and updates one BOE manifest per affected skill. Exactly one selection mode is required. At least one explicit `--assessor` is required. `--boe-root` is the only formal output location and is never inferred from the working directory, repository layout, runner cache, or environment.

```text
skill-assessment verify-boe --skill <path> <boe-directory>
```

`verify-boe` validates the selected skill package, reads `<boe-directory>/boe.json`, validates it against `boe/v1`, verifies every listed report exists beneath `<boe-directory>`, verifies every report digest, and performs only the minimal raw-output check needed to identify the assessor that produced the report. It does not validate the assessor's full output schema, require assessor credentials, run assessors, access the network, or inspect catalog policy.

## First supported assessor

The first assessment-kit release supports one assessor: `skillspector`.
Customer-facing documentation must link to the NVIDIA SkillSpector source at
`https://github.com/NVIDIA/SkillSpector` from the SkillSpector prerequisite and
assessor-configuration sections.

The kit invokes SkillSpector with the selected skill package path as its
positional input, JSON output format, and an explicit native output file path
under the command output directory. The adapter must fail before invocation if
the `skillspector` executable is unavailable, its version is unsupported, the
configured scan mode is unsupported, or required LLM configuration is missing
for `llm-assisted`.

The adapter invocation contract is:

```text
<skillspector-executable> scan \
  <skill-package-path> \
  --format json \
  --output <native-output-path>
```

For an explicit `static-only` assessment, the adapter appends `--no-llm`.
There is no SkillSpector `--mode` argument. For `llm-assisted`, the adapter does
not append `--no-llm`.

For `llm-assisted`, the first release supports the `openai_compatible` provider
profile used by the maintainer proof. It requires all four public variables and
maps them to SkillSpector's native process environment:

| Assessment-kit variable | SkillSpector process variable |
|---|---|
| `SKLC_LLM_PROVIDER=openai_compatible` | `SKILLSPECTOR_PROVIDER=openai_compatible` |
| `SKLC_LLM_API_KEY` | `SKILLSPECTOR_COMPAT_API_KEY` |
| `SKLC_LLM_BASE_URL` | `SKILLSPECTOR_COMPAT_BASE_URL` |
| `SKLC_LLM_MODEL` | `SKILLSPECTOR_MODEL` |

The adapter-provided mapping overrides conflicting inherited SkillSpector
variables for these settings so ambient process state cannot silently change
the selected provider, endpoint, model, or credential. Supporting another
provider profile requires a documented mapping and compatibility tests in a
later release. `static-only` may be used only when explicitly configured; LLM
variables are optional for explicit `static-only` runs and must not be required.
The adapter writes the assessor's stdout and stderr to command diagnostics, not
to the native report file. SkillSpector exit `0` means a completed scan below
its finding threshold and exit `1` may mean a completed scan with findings.
Either exit is accepted only when the native report file exists, parses as a
JSON object, identifies the supported SkillSpector version, and reports
`execution_successful: true`. Exit `2`, a missing report, malformed JSON, or any
other `execution_successful` value is an assessor execution failure even if
partial output exists.

For `llm-assisted`, a report is also rejected when its metadata says LLM was not
requested, the LLM was unavailable, or LLM execution was degraded. In
particular, `metadata.llm_requested` must be `true`,
`metadata.llm_available` must be `true`, and
`metadata.llm_degraded` must not be `true`. This prevents SkillSpector from
silently supplying partial static-only coverage when LLM execution was
configured.

The default scan mode is `llm-assisted`. Missing LLM configuration fails closed;
the kit must not fall back to `static-only` when `llm-assisted` is configured or
selected by default. The default assessor timeout is 600
seconds per skill and assessor pair. Both defaults must be documented and
overridable through `--config`; missing required values after documented
defaults and overrides are applied fail closed.

Retry behavior is limited to assessor execution failures that exit without a
valid native report and rejected degraded `llm-assisted` reports. For
`llm-assisted`, LLM rate limiting, including HTTP `429`, and report metadata
showing degraded LLM execution are retryable assessor execution failures. The
first release attempts each skill and assessor pair once. It reports retryable
failures with exit code `10` so CI can decide whether to retry the job. The CLI
must not retry internally unless a later release documents the retry count and
backoff. The CLI must not fall back to `static-only` after a retryable
`llm-assisted` failure.

Assessor identity is determined from the retained JSON report. For
SkillSpector, `verify-boe` reads enough JSON to confirm the report identifies
SkillSpector as its producer, using either `metadata.assessor: "skillspector"`,
`metadata.tool: "skillspector"`, or `metadata.skillspector_version`. Missing
assessor identity or malformed JSON fails verification. `verify-boe` does not
attempt to detect assessor semver mistakes or defects in the assessor's own
report schema.

The minimal recognized SkillSpector native JSON shape is:

```json
{
  "metadata": {
    "skillspector_version": "<version>"
  }
}
```

Additional assessor-owned fields are retained unchanged and ignored by BOE
verification.

## Selection rules

`validate`, `advise`, and `assess` accept repeated `--skill <path>` arguments or `--root <path>`.

Selection produces a set of unpacked skill package directories. `--root`
recursively discovers the outermost directories containing `SKILL.md` and does
not descend into an identified package, so a package-owned nested `SKILL.md`
does not become a second package. Discovery does not follow symbolic links.
The root itself may be selected when it contains `SKILL.md`. Relative selections
such as `--skill .` and `--root .` use the resolved package directory name.
Unreadable discovery roots or subdirectories fail the whole selection instead
of silently skipping packages. LF and CRLF frontmatter are accepted without
altering the bytes used for the content digest. Optional metadata fields may
be omitted, but explicit null values must satisfy the schema's types and are
rejected where the schema requires an object, string, or array.

An empty `--root` selection succeeds without writing advice artifacts,
assessor output, or BOE updates. A non-empty selection fails before scanning if
any discovered package is invalid, if two selected packages resolve to the same
standard skill name, or if a selected output directory is inside a selected
skill package.

## Configuration and environment

`--config <path>` is an optional assessment-kit JSON configuration file with
assessor-specific settings namespaced under `assessors.<assessor-id>`. It is
not an assessor-native configuration file. The assessment kit validates this
file and applies supported settings using normal CLI precedence:

```text
command argument > environment variable > config file > documented default
```

The config file top-level shape is:

```json
{
  "assessors": {
    "<assessor-id>": {
      "<setting>": "<non-secret value>"
    }
  }
}
```

The first release accepts only the `assessors.skillspector` configuration block.
Unknown assessor IDs, unknown configuration keys, and invalid values fail before
scanning. Secrets must be supplied through environment variables, not the config
file.

For `assessors.skillspector`, the first release supports these non-secret config
keys:

- `scan_mode`: `llm-assisted` or `static-only`.
- `timeout_seconds`: positive integer timeout per skill and assessor pair.

The matching environment variables are:

- `SKLC_SKILLSPECTOR_SCAN_MODE`
- `SKLC_SKILLSPECTOR_TIMEOUT_SECONDS`

The assessment kit may not pass the config file path through to SkillSpector as
native config, and the first release does not expose arbitrary SkillSpector
configuration passthrough.

The released `docs/assessor-configuration.md` must include this minimal default
example:

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

It must also state that omitting `--config` uses the documented defaults, and
that an explicit config file is needed only when the user changes a supported
non-secret setting.

For SkillSpector, the default secret and endpoint environment variables are
`SKLC_LLM_API_KEY`, `SKLC_LLM_BASE_URL`, `SKLC_LLM_MODEL`, and
`SKLC_LLM_PROVIDER`. There are no silent fallback credentials, endpoints,
assessor IDs, output directories, or BOE directories. Missing required
configuration fails closed, and diagnostics must not print secret values.

The released CLI documentation must distinguish command arguments from
environment variables. Local command-line runs use command arguments for skill
selection and output paths; the CLI does not read environment variables for
`--root`, `--skill`, `--output`, `--boe-root`, `--assessor`, or `--config`
unless a later release explicitly adds and documents those aliases.

## Generated files

`validate` writes no files.

`advise` writes only:

```text
<output>/
  advice.md
  advice-manifest.json
  native/
    <assessor-id>/
      <skill-name>/
        <raw-report-sha256>.json
```

`advice.md` is an index and summary over retained native reports, not a
publication decision or normalized assessment report. It must contain these
sections:

- `# Skill Assessment Advice`
- `## Scope` listing selected skill names and assessor IDs
- `## Native Reports` listing each retained report path and SHA-256 digest
- `## Findings Summary` containing actionable assessor-derived findings or
  `No summary produced`

For supported native report formats, `## Findings Summary` must preserve the
actionable fields from each finding when present, including severity, category,
location, finding text, pattern, confidence, explanation, and remediation. The
summary may group duplicate findings, but it must not omit distinct actionable
findings from a successful native report. For the supported SkillSpector version,
the source is its native `issues` array. The summary preserves all fields of
each issue, including code snippets, evidence, and additional occurrences.

Native report files are the assessor's original output bytes. The kit must not
replace native output with a SkLC-normalized report and must not modify native
output before computing its digest. Advice output must not create BOE.
`advice-manifest.json` must conform to the assessment-artifacts v1
`advice-manifest.schema.json` and record `advice.md` plus every retained native
report path and digest.

`assess` writes only beneath `--boe-root`:

```text
<boe-root>/
  <skill-name>/
    boe.json
    assessments/
      <assessor-id>/
        <raw-report-sha256>.json
```

`<raw-report-sha256>` is the lowercase SHA-256 hex digest of the exact native report bytes, without a prefix. Report file names use that digest plus the native report file extension documented for the assessor. BOE entries record paths relative to the directory containing `boe.json`, with no leading slash and no `..` segment.

The core `assess` command does not write `assessment-manifest.json` or
`verify-boe.log`. When its output is retained as an assessment artifact root,
the caller or CI profile writes those files beside `boe/` after verification.
`assessment-manifest.json` must conform to the assessment-artifacts v1
`assessment-manifest.schema.json`.

## BOE update and digest rules

`assess` writes a native report file before updating `boe.json`. The BOE entry then records:

```json
{
  "path": "assessments/<assessor-id>/<raw-report-sha256>.json",
  "sha256": "sha256:<raw-report-sha256>"
}
```

The BOE manifest also binds those reports to the exact selected package:

```json
{
  "schema_version": "skill-exchange-boe/v1",
  "skill": {
    "name": "<skill-name>",
    "content_sha256": "sha256:<skill-content-sha256>"
  },
  "assessments": [
    {
      "path": "assessments/<assessor-id>/<raw-report-sha256>.json",
      "sha256": "sha256:<raw-report-sha256>"
    }
  ]
}
```

`verify-boe` derives the assessor ID from each BOE report path. The path must
match `assessments/<assessor-id>/<raw-report-sha256>.json`; the assessor ID is
the first path segment after `assessments/`. For the first release, the only
accepted assessor ID is `skillspector`. The filename stem must match the report
digest and the file extension must be `.json`.

If `boe.json` does not exist for a skill, `assess` creates it with
`schema_version` set to `skill-exchange-boe/v1`, the selected skill name and
content digest, and an `assessments` array containing the new entry or entries.
If it already exists, `assess` validates it before adding entries and rejects it
when its skill name or content digest does not match the selected package.
Existing matching-content entries are preserved. An entry already present with
the same path and digest is idempotent. A digest-named report file that already
exists with different bytes is an error. A failed, timed-out, unsupported, or
malformed assessor report creates no BOE entry.

BOE update output must be deterministic: entries are unique by `(path, sha256)`
and written in a stable order. Apart from the selected skill identity and
content digest, the BOE manifest records only relative report paths and SHA-256
hashes. It does not duplicate assessment content, assessor configuration, run
identifiers, source-system references, publication decisions, or
cross-assessor risk summaries.

## Exit and failure semantics

- `0`: all requested work completed. An empty `--root` selection is successful and writes no assessor output or BOE updates.
- `2`: invalid invocation, invalid package, invalid selection, duplicate selected skill names, invalid configuration, unsupported assessor ID or version, unreadable BOE, BOE schema failure, BOE skill identity or content mismatch, missing referenced report, digest mismatch, missing assessor identity, malformed native report, non-retryable assessor execution failure, or filesystem write failure.
- `10`: one or more retryable assessor failures, including timeout, temporary assessor execution failure (exit `75`), `llm-assisted` LLM rate limiting such as HTTP `429`, or rejected degraded LLM coverage.

When a batch contains both retryable and permanent pair failures, exit `10`
takes precedence and diagnostics describe every failure. Callers must inspect
those diagnostics before deciding whether retrying can complete the batch.
An advice write failure does not override an earlier retryable pair failure.
Rate-limit classification examines complete redacted diagnostics before
truncating the displayed text.

Commands report human-readable diagnostics to stderr and do not print secrets. Invalid invocation, invalid selection, invalid package, or invalid configuration fails before assessor execution and before writing generated files. During `advise` or `assess`, a failure for one skill or assessor must not create a native report or BOE entry for that failed pair. Successfully completed independent pairs may remain on disk, but the command exits non-zero when any requested pair fails.

## Contracts

The release consumes and produces:

- Skill-package contract `urn:skill-exchange:skill-package:v1`.
- BOE contract `skill-exchange-boe/v1`.
- Assessment-artifacts contract `skill-exchange-assessment-artifacts/v1`.
- Release-manifest contract `skill-exchange-release-manifest/v1`.
- Native assessor output, retained unchanged.

## Local proof

Acceptance requires a clean temporary workspace that:

1. Receives the assessment-kit archive and its product-qualified manifest and
   checksum sidecars from GitHub Releases.
2. Verifies the archive and external manifest before extraction, confirms the
   internal and external manifests are identical, and verifies the extracted
   files with the internal checksum file.
3. Installs the wheel in an isolated Python environment.
4. Configures SkillSpector and assessment-kit settings without relying on
   repository-specific defaults.
5. Runs `skill-assessment validate` against one or more local skill packages.
6. Runs `skill-assessment advise` and confirms the advice output follows the
   assessment-artifacts v1 contract.
7. Runs `skill-assessment assess` and confirms the retained native reports and
   BOE output follow the BOE-manifest v1 contract. The assessment-artifacts v1
   assessment manifest and verification log are caller-owned outputs exercised
   by the later GitLab CI profile proof.
8. Verifies the produced BOE with `skill-assessment verify-boe`.

This proof must not require a GitLab project, GitLab CI, catalog assembly, site
build, deployment, commits, pushes, or provider API calls beyond those needed by
the configured assessor.

The branch CI also runs a release-candidate proof: it builds a real wheel and
archive, verifies both checksum layers and manifest identity, installs into an
isolated Python 3.12 environment, and runs all four public commands with the
pinned SkillSpector in explicit static mode. The installed CLI receives no
repository Python path, and its outputs are checked against the extracted
schemas. This catches packaging defects before tagging; the GitHub Release
download proof above remains required for release acceptance.

## Exclusions

- Catalog assembly.
- Catalog-policy evaluation.
- Site build or deployment.
- Source-control commits or pushes.
- GitHub or GitLab API calls from the core runtime.
