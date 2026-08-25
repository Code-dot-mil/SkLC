# Bill of Evidence Contract v1

A BOE is the durable, integrity-verifiable envelope around one assessment of one exact skill-package content hash. `boe.json` conforms to `boe.schema.json`; companion files preserve the normalized summary, assessor configuration, and native report.

```text
<boe-directory>/
  boe.json
  summary.json
  scanner-config.json
  hashes.json
  native/
    <assessor-report>
```

Paths recorded in `boe.json` are relative to the BOE directory. `hashes.json` maps every other required BOE file to its lowercase hexadecimal SHA-256 digest and does not hash itself.

Catalog tooling verifies the schema version, skill identity, content hash, scan cache key, required paths, and every declared hash before considering the evidence for admission.

Only BOE in a catalog release's supported major version is eligible for that catalog. Legacy BOE can remain as historical evidence and its mere presence is not an error. A currently served skill must have matching current-schema BOE or be reassessed or excluded.
