"""Offline verification of a deployment-kit-prebuilt package (Python 3.12+)."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

SCHEMA_PATH = "contracts/release-manifest/v1/release-manifest.schema.json"
ROOT_METADATA = {"release-manifest.json", "SHA256SUMS.txt"}
REQUIRED_FILES = {
    ".gitlab-ci.yml", "README.md", "docs/install.md", "docs/deploy-gitlab-pages.md",
    "docs/deploy-static-hosting.md", "scripts/verify_prebuilt.py", SCHEMA_PATH, "public/index.html",
}
SCHEMA_KEYWORDS = {
    "$schema", "$id", "title", "$defs", "$ref", "type", "required", "properties",
    "additionalProperties", "const", "minLength", "format", "pattern", "minItems", "items", "uniqueItems",
}
DATE_TIME = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}[Tt](?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]"
    r"(?:\.[0-9]+)?(?:[Zz]|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])"
)
JS_TOKENS = re.compile(
    r"(?P<ignored>\s+|//[^\r\n\u2028\u2029]*|/\*[\s\S]*?\*/)|"
    r'''(?P<string>"(?:\\[\s\S]|[^"\\])*"|'(?:\\[\s\S]|[^'\\])*'|`(?:\\[\s\S]|[^`\\])*`)|'''
    r"(?P<word>[\w$]+)|(?P<operator>\+\+|--|=>|[^\s])"
)
JS_REGEXP = re.compile(
    r"/(?![*/])(?:\\[^\r\n\u2028\u2029]|"
    r"\[(?:\\[^\r\n\u2028\u2029]|[^\]\\\r\n\u2028\u2029])*\]|"
    r"[^/\\[\r\n\u2028\u2029])+/[a-zA-Z]*"
)
JS_EXPRESSION_PREFIXES = {"return", "throw", "case", "delete", "void", "typeof", "new", "in", "instanceof",
                          "yield", "await", "else", "do", "of"}
JS_CONTROL_PARENS = {"if", "while", "for", "with", "switch", "catch"}
JS_ESCAPE = re.compile(r"\\(?:u\{[0-9a-fA-F]+\}|u[0-9a-fA-F]{4}|x[0-9a-fA-F]{2}|\r\n|[\s\S])")


class VerificationError(ValueError):
    pass


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise VerificationError(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)


def _check_schema(rule: dict) -> None:
    """Fail closed if the vendored v1 schema starts using unsupported features."""
    if not isinstance(rule, dict) or set(rule) - SCHEMA_KEYWORDS:
        raise VerificationError("unsupported release-manifest schema keywords")
    if "type" in rule and rule["type"] not in {"object", "array", "string"}:
        raise VerificationError("unsupported release-manifest schema type")
    if "format" in rule and rule["format"] != "date-time":
        raise VerificationError("unsupported release-manifest schema format")
    for keyword in ("$defs", "properties"):
        for child in rule.get(keyword, {}).values():
            _check_schema(child)
    for keyword in ("items", "additionalProperties"):
        if isinstance(rule.get(keyword), dict):
            _check_schema(rule[keyword])


def _validate(value, rule: dict, schema: dict, location: str = "$", refs: tuple[str, ...] = ()) -> None:
    if "$ref" in rule:
        reference = rule["$ref"]
        if not reference.startswith("#/") or reference in refs:
            raise VerificationError(f"unsupported schema reference: {reference}")
        target = schema
        for part in reference[2:].split("/"):
            target = target[part.replace("~1", "/").replace("~0", "~")]
        _validate(value, target, schema, location, (*refs, reference))
    expected = rule.get("type")
    if expected and not isinstance(value, {"object": dict, "array": list, "string": str}[expected]):
        raise VerificationError(f"{location} must be a {expected}")
    if "const" in rule and value != rule["const"]:
        raise VerificationError(f"{location} must equal {rule['const']!r}")
    if isinstance(value, str):
        if len(value) < rule.get("minLength", 0):
            raise VerificationError(f"{location} is too short")
        if "pattern" in rule and re.search(rule["pattern"], value) is None:
            raise VerificationError(f"{location} does not match its required pattern")
        if rule.get("format") == "date-time":
            if DATE_TIME.fullmatch(value) is None:
                raise VerificationError(f"{location} is not a valid date-time")
            try:
                datetime.fromisoformat(value.upper().replace("Z", "+00:00"))
            except ValueError as error:
                raise VerificationError(f"{location} is not a valid date-time") from error
    if isinstance(value, list):
        if len(value) < rule.get("minItems", 0):
            raise VerificationError(f"{location} has too few items")
        if rule.get("uniqueItems"):
            keys = [json.dumps(item, sort_keys=True) for item in value]
            if len(keys) != len(set(keys)):
                raise VerificationError(f"{location} contains duplicate items")
        if "items" in rule:
            for index, item in enumerate(value):
                _validate(item, rule["items"], schema, f"{location}[{index}]", refs)
    if isinstance(value, dict):
        missing = set(rule.get("required", [])) - value.keys()
        if missing:
            raise VerificationError(f"{location} is missing required fields: {sorted(missing)}")
        properties = rule.get("properties", {})
        additional = rule.get("additionalProperties", True)
        for name, item in value.items():
            if name in properties:
                _validate(item, properties[name], schema, f"{location}.{name}", refs)
            elif additional is False:
                raise VerificationError(f"{location} contains unexpected field: {name}")
            elif isinstance(additional, dict):
                _validate(item, additional, schema, f"{location}.{name}", refs)


def _reject_link(path: Path) -> None:
    if path.is_symlink() or path.is_junction():
        raise VerificationError(f"package must not contain links: {path}")


def _safe_path(root: Path, relative: str) -> Path:
    parts = relative.split("/")
    if (
        any(part in {"", ".", ".."} for part in parts)
        or "\\" in relative or ":" in relative
        or any(ord(char) < 32 or ord(char) == 127 for char in relative)
    ):
        raise VerificationError(f"unsafe package path: {relative!r}")
    path = root
    for part in parts:
        path = path / part
        _reject_link(path)
    if not path.resolve().is_relative_to(root):
        raise VerificationError(f"path escapes the package: {relative!r}")
    return path


def _files(root: Path) -> dict[str, Path]:
    result = {}
    pending = [root]
    while pending:
        for path in pending.pop().iterdir():
            if path.parent == root and path.name == ".git":
                continue  # A customer's Git checkout is not a release asset.
            _reject_link(path)
            relative = path.relative_to(root).as_posix()
            _safe_path(root, relative)
            if path.is_dir():
                pending.append(path)
            elif path.is_file():
                result[relative] = path
            else:
                raise VerificationError(f"not a regular package file: {relative}")
    return result


def _sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def _decode_escape(match: re.Match) -> str:
    escaped = match.group()[1:]
    if escaped.startswith("u{"):
        return chr(int(escaped[2:-1], 16))
    if escaped.startswith(("u", "x")) and len(escaped) > 1:
        return chr(int(escaped[1:], 16))
    return {"n": "\n", "r": "\r", "t": "\t", "b": "\b", "f": "\f", "v": "\v",
            "\n": "", "\r": "", "\r\n": ""}.get(escaped, escaped)


def _js_strings(text: str):
    # Read tokens in order so quotes and comment markers inside /patterns/ never
    # start strings/comments. Track operand positions to keep division separate.
    position, previous = 0, ""
    expression_start = True
    parens: list[bool] = []
    blocks: list[bool] = []
    functions: list[tuple[int, bool]] = []
    while position < len(text):
        match = JS_TOKENS.match(text, position)
        assert match is not None  # The final token alternative covers every non-whitespace character.
        position = match.end()
        literal = match.group()
        if match.lastgroup == "ignored":
            continue
        if literal == "/" and expression_start:
            pattern = JS_REGEXP.match(text, match.start())
            if pattern is None:
                raise VerificationError("cannot read JavaScript regular-expression literal")
            position = pattern.end()
            previous, expression_start = "regexp", False
            continue
        if match.lastgroup != "string":
            if literal == "(":
                parens.append(previous in JS_CONTROL_PARENS)
                expression_start = True
            elif literal == ")":
                expression_start = parens.pop() if parens else False
            elif literal == "{":
                if previous == ")" and functions and functions[-1][0] == len(parens):
                    # A function expression is an operand; a declaration ends a statement.
                    blocks.append(not functions.pop()[1])
                else:
                    blocks.append(previous in {"", ";", "{", "}", ")", "=>", "else", "try", "finally", "do"})
                expression_start = True
            elif literal == "}":
                expression_start = blocks.pop() if blocks else True
            elif match.lastgroup == "word":
                if literal == "function" and previous != ".":
                    functions.append((len(parens), previous not in {"", ";", "{", "}", "export", "default"}))
                expression_start = literal in JS_EXPRESSION_PREFIXES and previous != "."
            elif literal not in {"++", "--"}:
                expression_start = literal not in {".", "]"}
            previous = literal
            continue
        previous, expression_start = "string", False
        if literal.startswith("`") and "${" in literal:
            continue
        # Dynamic concatenation is outside the static download-reference contract.
        before, after = match.start() - 1, match.end()
        while before >= 0 and text[before].isspace():
            before -= 1
        while after < len(text) and text[after].isspace():
            after += 1
        if (before >= 0 and text[before] == "+") or (after < len(text) and text[after] == "+"):
            continue
        yield JS_ESCAPE.sub(_decode_escape, literal[1:-1])


class _HTMLReferences(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.values: list[str] = []
        self.in_script = False

    def handle_starttag(self, tag, attrs):
        self.values.extend(value for name, value in attrs if name in {"href", "src"} and value is not None)
        if tag == "script":
            self.in_script = True

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_script = False

    def handle_data(self, data):
        if self.in_script:
            self.values.extend(_js_strings(data))


def _json_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _json_strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _json_strings(item)


def _check_downloads(root: Path, files: dict[str, Path]) -> None:
    for relative, file in files.items():
        if not relative.startswith("public/") or file.suffix.lower() not in {".html", ".json", ".js"}:
            continue
        text = file.read_text(encoding="utf-8")
        if file.suffix.lower() == ".html":
            parser = _HTMLReferences()
            parser.feed(text)
            parser.close()
            values = parser.values
        elif file.suffix.lower() == ".json":
            values = _json_strings(json.loads(text, object_pairs_hook=_unique_object))
        else:
            values = _js_strings(text)
        for value in values:
            try:
                parsed = urlsplit(value.strip())
            except ValueError:
                if value.strip().startswith(("downloads/", "./downloads/", "/downloads/")):
                    raise
                continue  # An unrelated text value is not necessarily a URL.
            if parsed.scheme or parsed.netloc:
                continue
            path = unquote(parsed.path, errors="strict")
            while path.startswith("./"):
                path = path[2:]
            if path.startswith("/downloads/"):
                raise VerificationError(f"download URL must be relative in {relative}: {value!r}")
            if not path.startswith("downloads/"):
                continue
            target = _safe_path(root, f"public/{path}")
            if not target.is_file():
                raise VerificationError(f"missing referenced download in {relative}: {value!r}")


def verify_package(root: Path, expected_version: str | None = None) -> None:
    _reject_link(root)
    root = root.resolve()
    files = _files(root)
    missing = (REQUIRED_FILES | ROOT_METADATA) - files.keys()
    if missing:
        raise VerificationError(f"missing required package files: {sorted(missing)}")
    for relative in ("public/assets", "public/downloads"):
        if not _safe_path(root, relative).is_dir():
            raise VerificationError(f"missing required package directory: {relative}")
    manifest = _load_json(files["release-manifest.json"])
    schema = _load_json(files[SCHEMA_PATH])
    _check_schema(schema)
    _validate(manifest, schema, schema)
    if manifest["product"] != "deployment-kit-prebuilt":
        raise VerificationError("release-manifest.json is not for deployment-kit-prebuilt")
    if expected_version is not None and manifest["version"] != expected_version:
        raise VerificationError("manifest version does not match the expected archive version")
    recorded = {}
    for entry in manifest["artifacts"]:
        relative = entry["path"]
        _safe_path(root, relative)
        if relative in recorded:
            raise VerificationError(f"duplicate manifest path: {relative}")
        recorded[relative] = entry["sha256"].removeprefix("sha256:")
    if set(recorded) != files.keys() - ROOT_METADATA:
        raise VerificationError("manifest file list does not match the package contents")
    checksums = {}
    for number, line in enumerate(files["SHA256SUMS.txt"].read_text(encoding="utf-8").splitlines(), 1):
        match = re.fullmatch(r"([a-f0-9]{64})  (.+)", line)
        if match is None:
            raise VerificationError(f"invalid checksum entry on line {number}")
        digest, relative = match.groups()
        _safe_path(root, relative)
        if relative in checksums:
            raise VerificationError(f"duplicate checksum path: {relative}")
        checksums[relative] = digest
    if recorded != checksums:
        raise VerificationError("release-manifest.json and SHA256SUMS.txt do not match")
    for relative, digest in recorded.items():
        if _sha256(files[relative]) != digest:
            raise VerificationError(f"checksum mismatch: {relative}")
    _check_downloads(root, files)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, nargs="?", default=Path.cwd())
    parser.add_argument("--expected-version", help="match the version selected during archive extraction")
    args = parser.parse_args()
    try:
        verify_package(args.root, args.expected_version)
    except (ValueError, OSError, KeyError, TypeError, RecursionError) as error:
        print(f"Prebuilt verification failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    print("Prebuilt package verified: manifest, checksums, files, and downloads are valid.")


if __name__ == "__main__":
    main()
