# Generated files

`validate` writes no files.

`advise --output <directory>` writes an advice artifact root:

```text
<directory>/
  advice.md
  advice-manifest.json
  native/
    skillspector/
      <skill-name>/
        <raw-report-sha256>.json
```

Files below `native/` are the exact bytes written by SkillSpector. `advice.md`
is an author-facing summary. `advice-manifest.json` binds the summary and native
reports to their SHA-256 digests and follows the assessment-artifacts v1 advice
schema. The whole `<directory>` is safe to retain as the advice job artifact.

`assess --boe-root <directory>` writes only the formal evidence tree:

```text
<directory>/
  <skill-name>/
    boe.json
    assessments/
      skillspector/
        <raw-report-sha256>.json
```

Each native report is retained unchanged. `boe.json` follows BOE v1 and binds
the reports to the package name and deterministic package-content digest. The
core command does not create `assessment-manifest.json` or `verify-boe.log`.

A CI caller that retains an assessment-artifacts v1 root passes
`<assessment-output>/boe` as `--boe-root`, writes `verify-boe.log` after calling
`verify-boe` for each skill, and then writes `assessment-manifest.json` beside
the `boe/` directory. The caller retains the complete `<assessment-output>`.
