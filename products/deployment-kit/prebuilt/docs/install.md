# Install the prebuilt deployment kit

## Prerequisites

Choose either GitLab Pages or another static hosting service before continuing.
Both paths require a program capable of extracting `.tar.gz` archives. Python 3
is required for the offline manifest and checksum verification.
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
```

Then validate `release-manifest.json` against the vendored schema, verify every
digest in `SHA256SUMS.txt`, and confirm both files describe the same artifacts:

```sh
python3 - <<'PY'
import hashlib
import json
import pathlib
import re
from datetime import datetime

root = pathlib.Path.cwd().resolve()
manifest = json.loads((root / "release-manifest.json").read_text())
schema = json.loads((root / "contracts/release-manifest/v1/release-manifest.schema.json").read_text())

SUPPORTED_KEYWORDS = {
    "$schema", "$id", "title", "$defs", "$ref", "type", "required",
    "properties", "additionalProperties", "const", "minLength", "format",
    "pattern", "minItems", "items", "uniqueItems",
}
TYPE_MAP = {"object": dict, "array": list, "string": str}
DATE_TIME = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})"
)


def fail(message):
    raise SystemExit(f"release-manifest.json does not conform to the vendored schema: {message}")


def resolve(reference):
    if not reference.startswith("#/"):
        fail(f"unsupported schema reference {reference!r}")
    rule = schema
    for part in reference[2:].split("/"):
        rule = rule[part.replace("~1", "/").replace("~0", "~")]
    return rule


def validate(value, rule, location="$"):
    unsupported = set(rule) - SUPPORTED_KEYWORDS
    if unsupported:
        fail(f"unsupported schema keywords at {location}: {sorted(unsupported)}")
    if "$ref" in rule:
        validate(value, resolve(rule["$ref"]), location)
        return
    expected = rule.get("type")
    if expected:
        expected_type = TYPE_MAP.get(expected)
        if expected_type is None:
            fail(f"unsupported schema type {expected!r} at {location}")
        if not isinstance(value, expected_type):
            fail(f"{location} must be a {expected}")
    if "const" in rule and value != rule["const"]:
        fail(f"{location} must equal {rule['const']!r}")
    if isinstance(value, str):
        if len(value) < rule.get("minLength", 0):
            fail(f"{location} is too short")
        if "pattern" in rule and re.search(rule["pattern"], value) is None:
            fail(f"{location} does not match its required pattern")
        if rule.get("format") == "date-time":
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError as error:
                fail(f"{location} is not a valid date-time: {error}")
            if DATE_TIME.fullmatch(value) is None or parsed.utcoffset() is None:
                fail(f"{location} is not a valid date-time")
        elif "format" in rule:
            fail(f"unsupported schema format {rule['format']!r} at {location}")
    if isinstance(value, list):
        if len(value) < rule.get("minItems", 0):
            fail(f"{location} has too few items")
        if rule.get("uniqueItems"):
            normalized = [json.dumps(item, sort_keys=True, separators=(",", ":")) for item in value]
            if len(normalized) != len(set(normalized)):
                fail(f"{location} contains duplicate items")
        if "items" in rule:
            for index, item in enumerate(value):
                validate(item, rule["items"], f"{location}[{index}]")
    if isinstance(value, dict):
        required = set(rule.get("required", []))
        missing = sorted(required - set(value))
        if missing:
            fail(f"{location} is missing required fields {missing}")
        properties = rule.get("properties", {})
        additional = rule.get("additionalProperties", True)
        for name, item in value.items():
            if name in properties:
                validate(item, properties[name], f"{location}.{name}")
            elif additional is False:
                fail(f"{location} contains unexpected field {name!r}")
            elif isinstance(additional, dict):
                validate(item, additional, f"{location}.{name}")


validate(manifest, schema)
if manifest["product"] != "deployment-kit-prebuilt":
    raise SystemExit("release-manifest.json is for the wrong product")
expected_root = f"deployment-kit-prebuilt-{manifest['version']}"
if root.name != expected_root:
    raise SystemExit(f"expected extracted directory {expected_root!r}, found {root.name!r}")

recorded = {}
for entry in manifest["artifacts"]:
    path = entry["path"]
    if path in recorded:
        raise SystemExit(f"duplicate manifest path: {path}")
    recorded[path] = entry["sha256"].removeprefix("sha256:")

checksums = {}
for line_number, line in enumerate((root / "SHA256SUMS.txt").read_text().splitlines(), 1):
    fields = line.split("  ", 1)
    if len(fields) != 2 or re.fullmatch(r"[a-f0-9]{64}", fields[0]) is None:
        raise SystemExit(f"invalid checksum entry on line {line_number}")
    digest, path = fields
    relative = pathlib.PurePosixPath(path)
    if not path or relative.is_absolute() or ".." in relative.parts:
        raise SystemExit(f"unsafe checksum path: {path}")
    target = root.joinpath(*relative.parts).resolve()
    if root not in target.parents:
        raise SystemExit(f"unsafe checksum path: {path}")
    if path in checksums:
        raise SystemExit(f"duplicate checksum path: {path}")
    if not target.is_file():
        raise SystemExit(f"checksum file is missing: {path}")
    if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
        raise SystemExit(f"checksum mismatch: {path}")
    checksums[path] = digest
if recorded != checksums:
    raise SystemExit("release-manifest.json and SHA256SUMS.txt do not match")
print("Release manifest and checksums are valid.")
PY
```

Use the extracted directory unchanged for GitLab Pages. For another host, the
`public/` directory is the site root.
