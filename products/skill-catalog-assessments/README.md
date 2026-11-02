# Current catalog assessments

Each `<skill-name>/` directory contains the latest successful `skillspector.json` and `adjudication.json` pair for that catalog skill. These two files are its BOE. The adjudication records `skill_sha256`; Git preserves earlier assessments.

## Download and review

Download `skill-catalog-assessments-<version>.zip` and `skill-catalog-<version>.zip` from the same [SkLC release](https://github.com/Code-dot-mil/SkLC/releases). Verify each asset's SHA-256 against the digest GitHub displays before extracting. For the assessment archive:

```sh
sha256sum skill-catalog-assessments-<version>.zip
```

Replace `<version>` with the release version. On macOS, use `shasum -a 256` in place of `sha256sum`. Compare the 64-character digest, ignoring GitHub's `sha256:` prefix, and stop if it differs. After the comparison succeeds, extract:

```sh
unzip skill-catalog-assessments-<version>.zip -d skill-catalog-assessments
```

The archive contains this README and one directory per skill, each with its two JSON reports; no scanner logs are included.

Install the separate assessment-kit wheel using its [guide](https://github.com/Code-dot-mil/SkLC/blob/main/products/assessment-kit/README.md#installation). From an environment exposing `skill-assessment` on `PATH`, summarize one extracted pair:

```sh
skill-assessment summarize --assessment-dir ./skill-catalog-assessments/python-secure-code-review
```

Summarize needs no scanner or provider credentials. Review remediation, unresolved findings, false positives, scope, and limitations. Successful assessment is evidence, not a safety certification. The pair applies only to its exact skill package contents; reassess modified packages rather than reusing the release evidence.

## Upstream maintenance

The independent main assessment job maintains this evidence for the catalog's current skill contents, using the checked-out assessment kit in LLM-assisted mode. Matching successful assessments are reused through `assess --if-changed`. Developers can summarize the pair to review required remediation, unresolved findings, false positives, and assessment limitations.

`scanner.log` is diagnostic output, ignored by Git and excluded from BOE downloads. Failures retain diagnostic artifacts and do not commit failed results. After successful scanning, reports for removed or renamed skills are pruned; unrelated files remain untouched.
