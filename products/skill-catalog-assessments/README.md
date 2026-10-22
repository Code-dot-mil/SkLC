# Current catalog assessments

Each `<skill-name>/` directory contains the latest successful `skillspector.json` and `adjudication.json` pair for that catalog skill. These two files are its BOE. The adjudication records `skill_sha256`; Git preserves earlier assessments.

The independent main assessment job maintains this evidence for the catalog's current skill contents, using the checked-out assessment kit in LLM-assisted mode. Matching successful assessments are reused through `assess --if-changed`. Developers can summarize the pair to review required remediation, unresolved findings, false positives, and assessment limitations.

`scanner.log` is diagnostic output, ignored by Git and excluded from BOE downloads. Failures retain diagnostic artifacts and do not commit failed results. After successful scanning, reports for removed or renamed skills are pruned; unrelated files remain untouched.
