# Bill of Evidence Manifest Contract v1

A BOE manifest binds retained native assessor reports to one exact unpacked
skill package. `boe.json` conforms to `boe.schema.json` and has this layout:

```text
<boe-directory>/
  boe.json
  assessments/
    <assessor-id>/
      <raw-report-sha256>.json
```

The `skill.name` value is the standard skill name derived from the package
directory. `skill.content_sha256` is the skill-package v1 content digest,
including the `sha256:` prefix. Together they prevent evidence for one package
or package revision from being presented as evidence for another.

Each assessment entry contains only a report path and digest. Paths are
relative to the directory containing `boe.json`, must match
`assessments/<assessor-id>/<raw-report-sha256>.json`, and must remain beneath the
BOE directory after resolution. The filename digest, the entry's `sha256`
value, and the digest of the exact retained report bytes must agree.

The manifest does not duplicate native assessment content, assessor
configuration, run identifiers, source-system references, publication
decisions, or cross-assessor summaries. Assessor identity and version remain in
the retained native report. Consumers perform only the documented minimal
native-output check needed to identify its assessor; they do not reinterpret or
normalize assessor-owned output during integrity verification.

Assessment entries are unique by `(path, sha256)` and sorted deterministically
by path and then digest. A BOE contains at least one assessment. Symbolic links,
absolute paths, parent traversal, missing reports, malformed assessor identity,
and digest mismatches fail verification.

Catalog tooling verifies the schema, skill identity, current package content
digest, path containment, native assessor identity, and every report digest
before consuming the evidence. BOE presence or findings do not themselves make
a publication decision.

Only BOE in a catalog release's supported major version is eligible for that
catalog. Legacy BOE can remain as historical evidence and its mere presence is
not an error. Evidence for different package content must be stored separately
or replaced; it must not be appended to a manifest bound to another content
digest.
