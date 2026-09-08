# Install the prebuilt deployment kit

## Prerequisites

Choose either GitLab Pages or another static hosting service before continuing.
Both paths require a program capable of extracting `.tar.gz` archives and a
SHA-256 checksum utility. Python 3 is required for the offline manifest check.
The GitLab path also requires local Git and permission to push to the destination
project. See the
[Git user manual](https://git-scm.com/docs/user-manual) and
[first-time Git setup](https://git-scm.com/book/en/v2/Getting-Started-First-Time-Git-Setup)
if Git is not configured.

## Extract and verify

Replace `<version>` in the following command template with the version shown in
the downloaded archive filename:

```sh
version="<version>"
tar -xzf "deployment-kit-prebuilt-${version}.tar.gz"
cd "deployment-kit-prebuilt-${version}"
sha256sum -c SHA256SUMS.txt
```

Every checksum must report `OK`. Then validate the manifest structure and
confirm it describes the same files and digests as `SHA256SUMS.txt`:

```sh
python3 - <<'PY'
import json
import pathlib

root = pathlib.Path.cwd()
manifest = json.loads((root / "release-manifest.json").read_text())
schema = json.loads((root / "contracts/release-manifest/v1/release-manifest.schema.json").read_text())
required = set(schema["required"])
if not required <= set(manifest) or not set(manifest) <= set(schema["properties"]):
    raise SystemExit("release-manifest.json does not match the vendored schema fields")
if manifest.get("schema_version") != "skill-exchange-release-manifest/v1":
    raise SystemExit("release-manifest.json has the wrong schema version")
if manifest.get("product") != "deployment-kit-prebuilt":
    raise SystemExit("release-manifest.json is for the wrong product")
expected_root = f"deployment-kit-prebuilt-{manifest.get('version', '')}"
if root.name != expected_root:
    raise SystemExit(f"expected extracted directory {expected_root!r}, found {root.name!r}")
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

Use the extracted directory unchanged for GitLab Pages. For another host, the
`public/` directory is the site root.
