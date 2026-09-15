# Commands

Use repeated `--skill` arguments when the exact unpacked packages are known.
Use `--root` to recursively select every outermost package beneath a directory.
An outermost package is a directory containing `SKILL.md`; discovery does not
descend into it and does not require a namespace layout.

For example:

```text
workspace/
  team-a/
    secure-review/
      SKILL.md
  shared/
    unit-tests/
      SKILL.md
```

Validate both packages without writing files:

```text
skill-assessment validate --root workspace
```

Produce author-facing advice and retained native reports:

```text
skill-assessment advise --root workspace \
  --assessor skillspector \
  --output assessment-advice
```

Produce BOE for formal retention:

```text
skill-assessment assess --root workspace \
  --assessor skillspector \
  --boe-root assessment-output/boe
```

Verify one BOE against the exact package it assesses:

```text
skill-assessment verify-boe \
  --skill workspace/team-a/secure-review \
  assessment-output/boe/secure-review
```

To select packages explicitly, replace `--root workspace` with one or more
arguments such as `--skill workspace/team-a/secure-review --skill
workspace/shared/unit-tests`.

Arguments select skills, assessors, config files, and output paths. The CLI does
not read environment aliases for `--root`, `--skill`, `--assessor`, `--config`,
`--output`, or `--boe-root`.

A current-directory selection such as `--skill .` or `--root .` uses the
resolved package directory name. LF and CRLF frontmatter are accepted; the
content digest always uses the original file bytes. Explicit null values for
schema-typed metadata fields are invalid. Omit an unused optional field instead.
Unreadable directories fail discovery, including when other readable packages
have already been found. A truly empty root succeeds without creating output.
