# Four-skill Download Spec

## Outcome

Release the four existing developer skills as a download. Users extract the
archive and copy complete skill folders into their workspace's `.agents/skills/`.
This is roadmap milestone 3.3; the selected scope is a simple file distribution.

## Contents

`skill-catalog-<version>.tar.gz` contains:

```text
skill-catalog/
  README.md
  skills/
    python-secure-code-review/
    unit-test-generation/
    inline-documentation/
    code-change-description/
```

Each folder contains the committed `SKILL.md` and all committed supporting files
from `skills/ai4sdlc/<name>/`. Package exactly these four names. Fail on a missing
or empty `SKILL.md` or symbolic link. Do not include untracked files, other skills,
site content, BOE, policy files, schemas, manifests, or verification programs.

## Packaging and publication

`scripts/package-skill-catalog.sh <archive.tar.gz>` runs from the repository root
and packages `HEAD` using Git, Bash, tar, and sha256sum. It also writes an adjacent
`<archive.tar.gz>.sha256` file. Existing output files must not be overwritten.
No new Python code or dependency is needed for packaging.

CI independently uploads `skill-catalog.tar.gz` and its checksum as the
`skill-catalog` artifact. The existing tag-release workflow publishes the
versioned pair alongside the prebuilt site after its normal release checks.
The shared release manifest lists both product archives and the catalog checksum;
the shared `SHA256SUMS.txt` covers those assets and the manifest. This metadata
stays outside the catalog archive, which retains its individual checksum.

## Acceptance

The release tests extract the archive, verify its checksum, check exactly the
four skill folders and their unchanged supporting files, and check that missing
skills prevent publication and untracked local files are excluded.

The packaged README explains download, checksum verification, extraction, and
copying the folders. For published-release acceptance, follow it in a clean
workspace and confirm a fresh agent session discovers those workspace skills.
No assessment, selection policy, or custom installation tool is part of this
download.
