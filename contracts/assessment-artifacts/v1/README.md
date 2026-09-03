# Assessment Artifacts Contract v1

Assessment artifacts are retained outputs from assessment-kit advice and
assessment runs. This contract defines the filesystem layout that CI profiles,
operator tooling, and other consumers may rely on.

## Advice Artifacts

`skill-assessment advise --output <directory>` writes this tree:

```text
<directory>/
  advice.md
  native/
    <assessor-id>/
      <skill-name>/
        <raw-report-sha256>.json
```

`advice.md` is generated author-facing guidance. It is not BOE and does not
make publication decisions.

`advice.md` must include:

- `# Skill Assessment Advice`
- `## Scope` listing selected skill names and assessor IDs
- `## Native Reports` listing each retained report path and SHA-256 digest
- `## Findings Summary` containing actionable assessor-derived findings or
  `No summary produced`

For supported native report formats, `## Findings Summary` preserves the
actionable fields from each finding when present, including severity, category,
location, finding text, pattern, confidence, explanation, and remediation. It may
group duplicate findings, but it must not omit distinct actionable findings from
a successful native report.

Files under `native/` are assessor-native report bytes retained unchanged. The
assessment kit computes `<raw-report-sha256>` from those exact bytes and uses
the digest as the report filename stem.

## Assessment Artifacts

A retained assessment artifact root has this tree:

```text
<assessment-output>/
  boe/
    <skill-name>/
      boe.json
      assessments/
        <assessor-id>/
          <raw-report-sha256>.json
  verify-boe.log
```

`skill-assessment assess --boe-root <directory>` produces the content under
`boe/` when the caller passes `<assessment-output>/boe` as `--boe-root`.
The GitLab CI profile writes `verify-boe.log` beside `boe/` after running
`skill-assessment verify-boe` for each retained BOE directory.

Each `boe/<skill-name>/boe.json` follows `skill-exchange-boe/v1`. Report paths
inside `boe.json` are relative to the directory containing that `boe.json`.

## Path Rules

- `<skill-name>` follows the skill-package v1 name rules.
- `<assessor-id>` is a supported assessor identifier for the assessment-kit
  release that produced the artifact.
- Native report filenames use the lowercase SHA-256 hex digest of the exact
  native report bytes plus the assessor's documented file extension.
- Consumers must reject absolute paths, parent-directory traversal, duplicate
  skill names, and symbolic links that escape the artifact root.

## Ownership

The assessment kit owns this artifact layout. Assessor-native report content is
owned by the assessor and retained byte-for-byte. BOE manifest content is owned
by the assessment kit and governed by the BOE-manifest contract.
