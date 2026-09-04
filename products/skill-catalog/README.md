# SkLC Skill Catalog

This standalone catalog contains four developer-focused skills. It can seed a
GitLab-hosted exchange or distribute the skills directly without the assessment
kit or deployment kit.

The published skill set is exactly:

- `python-secure-code-review`
- `unit-test-generation`
- `inline-documentation`
- `code-change-description`

The archive contains the packages under `skills/`, the skill-package and release-
manifest contracts under `contracts/`, and integrity metadata in
`release-manifest.json` and `SHA256SUMS.txt`. A future release may also contain
optional evidence under `boe/<skill-name>/boe.json` with assessor reports below
`boe/<skill-name>/assessments/`; BOE does not determine which skills are
published.

From the extracted archive root, verify every released file:

```sh
sha256sum -c SHA256SUMS.txt
python3 - <<'PY'
import json
import pathlib

root = pathlib.Path.cwd()
manifest = json.loads((root / "release-manifest.json").read_text())
recorded = {entry["path"]: entry["sha256"].removeprefix("sha256:") for entry in manifest["artifacts"]}
checksums = {
    path: digest
    for line in (root / "SHA256SUMS.txt").read_text().splitlines()
    for digest, path in [line.split("  ", 1)]
}
if recorded != checksums:
    raise SystemExit("release-manifest.json and SHA256SUMS.txt do not match")
print("Release manifest and checksums match.")
PY
```

To make the skills available in a workspace, copy each directory beneath
`skills/` into that workspace's `.agents/skills/` directory, start the coding
agent from the workspace, and confirm that it reports each skill from the
workspace path. The same `skills/*` directories can be committed to the skills
location used by a GitLab-hosted exchange or distributed directly to developers.

This release uses the skill-package v1 and release-manifest v1 contracts. The BOE
v1 contract is included only in a release that contains optional BOE.
