# Skill Catalog Spec

## Decision baseline

This spec follows `docs/decisions.md`: the catalog is a standalone product released from GitHub and usable from GitLab without assessment or deployment products.

## Milestone

`docs/roadmap.md` section 3.3, Skill catalog.

## Status

Approved.

## Outcome

A customer obtains a governed catalog containing four developer-centered skills and can use it to seed a GitLab-hosted exchange or distribute the skills directly.

## Release artifact

Publish one archive named `skill-catalog-<version>.tar.gz`. The
unpacked archive root is `skill-catalog-<version>/` and contains:

```text
skill-catalog-<version>/
  README.md
  release-manifest.json
  SHA256SUMS.txt
  skills/
    python-secure-code-review/
      SKILL.md
      references/        optional, copied when present
      scripts/           optional, copied when present
      assets/            optional, copied when present
    unit-test-generation/
      SKILL.md
      references/        optional, copied when present
      scripts/           optional, copied when present
      assets/            optional, copied when present
    inline-documentation/
      SKILL.md
      references/        optional, copied when present
      scripts/           optional, copied when present
      assets/            optional, copied when present
    code-change-description/
      SKILL.md
      references/        optional, copied when present
      scripts/           optional, copied when present
      assets/            optional, copied when present
  contracts/
    skill-package/v1/
    release-manifest/v1/
    boe/v1/              only required when boe/ is included
  boe/                   optional
```

The archive contains no site source, generated site data, static-site output,
assessment runtime, GitHub workflow, GitLab CI file, or hidden local build
state.

## Skill packages

The catalog publishes exactly these four skills:

| Display purpose | Source package path | Released package path | Skill name |
| --- | --- | --- | --- |
| Secure Code Review | `skills/ai4sdlc/python-secure-code-review/` | `skills/python-secure-code-review/` | `python-secure-code-review` |
| Unit Test Generation | `skills/ai4sdlc/unit-test-generation/` | `skills/unit-test-generation/` | `unit-test-generation` |
| Inline Documentation | `skills/ai4sdlc/inline-documentation/` | `skills/inline-documentation/` | `inline-documentation` |
| Commit Message and PR Description | `skills/ai4sdlc/code-change-description/` | `skills/code-change-description/` | `code-change-description` |

Each released package follows the skill-package v1 contract. `SKILL.md` must
start with YAML frontmatter containing at least `name` and `description`; the
frontmatter `name` must match the package directory name. Copy every regular
file below each source package directory into the matching released package
directory. Reject symbolic links, paths that escape the package directory, and
duplicate skill names.

## Internal release policy

Catalog policy governs which source skills are included in the release. It is
an internal maintainer input and must not be included in the released archive.
The catalog-policy contract is also internal to release assembly and must not be
vendored in the released archive.

For the initial catalog, maintainer release assembly uses this policy:

```yaml
schema_version: skill-exchange-catalog-policy/v1
mode: include-list
skills:
  - python-secure-code-review
  - unit-test-generation
  - inline-documentation
  - code-change-description
```

The schema has exactly three fields:

- `schema_version`: the literal `skill-exchange-catalog-policy/v1`.
- `mode`: exactly one of `include-list` or `exclude-list`.
- `skills`: a unique list of skill names matching `^[a-z0-9](?:[a-z0-9-]{0,62})$`.

The initial catalog release uses `include-list` so the published set is exactly
the four listed skills. The policy supports no globs, path matching, tags,
namespaces, risk rules, BOE rules, or default mode. Every listed skill name must
resolve to exactly one valid release package; an unknown or duplicate name is a
release error.

## BOE and reports

BOE is optional for this milestone. Do not run assessment and do not require BOE
quality gates to publish the catalog. Include BOE only when it was produced by a
released assessment kit and conforms to the BOE-manifest v1 contract.

When BOE is included, place one manifest per skill under a directory named for
the skill name:

```text
boe/
  <skill-name>/
    boe.json
    assessments/
      <assessor-owned report files>
```

Each `boe/<skill-name>/boe.json` contains:

- `schema_version`: the literal `skill-exchange-boe/v1`.
- `assessments`: one or more entries with relative `path` and `sha256` fields.

Each assessment path is relative to the directory containing that skill's
`boe.json`, must not be absolute, and must not contain `..` path traversal. Each
referenced native assessor report must exist in the archive and its bytes must
match the recorded `sha256:<64 lowercase hex>` digest. BOE presence, absence,
or content never changes catalog publication; the internal catalog policy is the
publication decision for this milestone.

## README requirements

`README.md` must explain:

- the catalog purpose and the four included skills;
- that the catalog is a standalone GitHub release usable from GitLab without
  the assessment kit or deployment kit;
- the archive layout, including optional BOE;
- how to verify `SHA256SUMS.txt` and `release-manifest.json`;
- the exact published skill set;
- how to install the released skills into a workspace under `.agents/skills/`
  and confirm an agent discovers them from that workspace;
- how to copy `skills/*` into a GitLab-hosted exchange or distribute the skill
  packages directly to developers;
- that BOE is optional and does not affect publication; and
- which vendored contract versions the release uses.

## Release manifest and checksums

`release-manifest.json` conforms to
`contracts/release-manifest/v1/release-manifest.schema.json`. It contains
`schema_version: skill-exchange-release-manifest/v1`, the release `version`,
and an `artifacts` list whose entries have archive-relative `path` and
`sha256:<64 lowercase hex>` fields. The manifest records every file in the
archive except `release-manifest.json` and `SHA256SUMS.txt`. `SHA256SUMS.txt` records
the same archive-relative file digests in a standard checksum-file format
usable by `sha256sum -c`.

## Contracts

The release consumes:

- Skill-package contract v1 for `skills/*`.
- Release-manifest contract v1 for `release-manifest.json`.
- BOE-manifest contract v1 only when `boe/` is included.

## Local agent install proof

Acceptance requires a clean temporary workspace that:

1. Downloads `skill-catalog-<version>.tar.gz` from the GitHub Release.
2. Extracts the archive.
3. Runs `sha256sum -c SHA256SUMS.txt` from the archive root and confirms the file
   digests match `release-manifest.json`.
4. Confirms the four released package directories are present under `skills/`.
5. Validates each `skills/<skill-name>/SKILL.md` frontmatter against
   `contracts/skill-package/v1/skill.schema.json` and confirms each
   frontmatter `name` matches the directory name.
6. Confirms the published set is exactly:
   `python-secure-code-review`, `unit-test-generation`,
   `inline-documentation`, and `code-change-description`.
7. Confirms the archive does not contain `catalog-policy.yaml` or
   `contracts/catalog-policy/`.
8. Copies the extracted `skills/*` directories to
   `<workspace>/.agents/skills/*`.
9. Starts a supported agent session from `<workspace>` with temporary agent home
   and configuration directories so global agent and Codex skill sources are
   isolated or disabled.
10. Confirms the session discovers the four skills from
    `<workspace>/.agents/skills/*` and not from any global `.agents` or
    `.codex` skill source.
11. If `boe/` is present, validates each `boe/<skill-name>/boe.json` against
    `contracts/boe/v1/boe.schema.json`, confirms `<skill-name>` is one of the
    four published skill names, and recomputes each referenced report digest.

This proof may use shell or a local agent harness in the temporary workspace.
The evidence must include the discovered skill source paths. The proof must not
require a GitLab project, assessment execution, BOE production, site build,
GitLab Pages deployment, or operator-kit update support.

## Exclusions

- Assessment execution.
- BOE quality gates.
- Required BOE for publication.
- Publication changes based on BOE, assessor findings, risk, tags, or category.
- Site source or generated site data.
- Static site output.
