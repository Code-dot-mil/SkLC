from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from .errors import AssessmentError
from .packages import SKILL_NAME_RE, SkillPackage
from .skillspector import NativeReport

SHA256_RE = re.compile(r"^sha256:([a-f0-9]{64})$")
REPORT_PATH_RE = re.compile(r"^assessments/([a-z0-9](?:[a-z0-9-]{0,62}))/([a-f0-9]{64})\.json$")


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _require_safe_destination(path: Path, root: Path) -> None:
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise AssessmentError(f"generated path escapes command output root: {path}") from exc
    candidate = root
    for part in relative.parts:
        candidate /= part
        if candidate.is_symlink():
            raise AssessmentError(f"generated path must not traverse a symbolic link: {candidate}")


def _atomic_write(path: Path, content: bytes, *, root: Path) -> None:
    _require_safe_destination(path, root)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, path)
        except BaseException:
            Path(temporary_name).unlink(missing_ok=True)
            raise
    except OSError as exc:
        raise AssessmentError(f"cannot write {path}: {exc}") from exc


def write_native_report(path: Path, report: NativeReport, *, root: Path) -> str:
    digest = sha256_bytes(report.content)
    destination = path / f"{digest}.json"
    _require_safe_destination(destination, root)
    if destination.exists():
        try:
            existing = destination.read_bytes()
        except OSError as exc:
            raise AssessmentError(f"cannot read existing native report {destination}: {exc}") from exc
        if existing != report.content:
            raise AssessmentError(f"digest-named native report contains different bytes: {destination}")
    else:
        _atomic_write(destination, report.content, root=root)
    return digest


def _require_exact_keys(value: dict[str, Any], required: set[str], context: str) -> None:
    if set(value) != required:
        raise AssessmentError(f"{context} has invalid fields")


def validate_boe_document(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AssessmentError("boe.json must contain a JSON object")
    _require_exact_keys(value, {"schema_version", "skill", "assessments"}, "boe.json")
    if value["schema_version"] != "skill-exchange-boe/v1":
        raise AssessmentError("boe.json has an unsupported schema_version")
    skill = value["skill"]
    if not isinstance(skill, dict):
        raise AssessmentError("boe.json skill must be an object")
    _require_exact_keys(skill, {"name", "content_sha256"}, "boe.json skill")
    if not isinstance(skill["name"], str) or not SKILL_NAME_RE.fullmatch(skill["name"]):
        raise AssessmentError("boe.json has an invalid skill name")
    if not isinstance(skill["content_sha256"], str) or not SHA256_RE.fullmatch(skill["content_sha256"]):
        raise AssessmentError("boe.json has an invalid skill content digest")
    assessments = value["assessments"]
    if not isinstance(assessments, list) or not assessments:
        raise AssessmentError("boe.json assessments must be a non-empty array")
    identities: set[tuple[str, str]] = set()
    for entry in assessments:
        if not isinstance(entry, dict):
            raise AssessmentError("boe.json assessment entry must be an object")
        _require_exact_keys(entry, {"path", "sha256"}, "boe.json assessment entry")
        path = entry["path"]
        digest = entry["sha256"]
        if not isinstance(path, str) or not REPORT_PATH_RE.fullmatch(path):
            raise AssessmentError("boe.json has an invalid assessment path")
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            raise AssessmentError("boe.json has an invalid assessment digest")
        identity = (path, digest)
        if identity in identities:
            raise AssessmentError("boe.json contains a duplicate assessment entry")
        identities.add(identity)
    return value


def load_boe(path: Path) -> dict[str, Any]:
    if path.is_symlink():
        raise AssessmentError(f"BOE manifest must not be a symbolic link: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AssessmentError(f"cannot read BOE manifest {path}: {exc}") from exc
    return validate_boe_document(value)


def _report_identity(report: object, assessor_id: str) -> None:
    if assessor_id != "skillspector" or not isinstance(report, dict):
        raise AssessmentError("native report does not identify a supported assessor")
    metadata = report.get("metadata")
    if not isinstance(metadata, dict):
        raise AssessmentError("native report does not identify SkillSpector")
    identified = (
        metadata.get("skillspector_version")
        or metadata.get("assessor") == "skillspector"
        or metadata.get("tool") == "skillspector"
    )
    if not identified:
        raise AssessmentError("native report does not identify SkillSpector")


def verify_boe(package: SkillPackage, boe_directory: Path) -> None:
    if boe_directory.is_symlink():
        raise AssessmentError("BOE directory must not be a symbolic link")
    manifest = load_boe(boe_directory / "boe.json")
    expected_digest = f"sha256:{package.content_sha256}"
    if manifest["skill"] != {"name": package.name, "content_sha256": expected_digest}:
        raise AssessmentError("BOE skill identity or content digest does not match the selected package")
    root = boe_directory.resolve()
    for entry in manifest["assessments"]:
        relative = entry["path"]
        match = REPORT_PATH_RE.fullmatch(relative)
        assert match is not None
        assessor_id, filename_digest = match.groups()
        report_path = boe_directory / relative
        if report_path.is_symlink() or not report_path.is_file():
            raise AssessmentError(f"BOE native report is missing or invalid: {relative}")
        try:
            report_path.resolve().relative_to(root)
            content = report_path.read_bytes()
        except (OSError, ValueError) as exc:
            raise AssessmentError(f"cannot safely read BOE native report: {relative}") from exc
        digest = sha256_bytes(content)
        if digest != filename_digest or entry["sha256"] != f"sha256:{digest}":
            raise AssessmentError(f"BOE native report digest mismatch: {relative}")
        try:
            parsed = json.loads(content)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AssessmentError(f"BOE native report is malformed JSON: {relative}") from exc
        _report_identity(parsed, assessor_id)


def update_boe(package: SkillPackage, boe_root: Path, assessor_id: str, report: NativeReport) -> Path:
    directory = boe_root / package.name
    manifest_path = directory / "boe.json"
    if manifest_path.exists():
        manifest = load_boe(manifest_path)
        if manifest["skill"] != {
            "name": package.name,
            "content_sha256": f"sha256:{package.content_sha256}",
        }:
            raise AssessmentError("existing BOE skill identity or content digest does not match selected package")
        verify_boe(package, directory)
    else:
        manifest = {
            "schema_version": "skill-exchange-boe/v1",
            "skill": {"name": package.name, "content_sha256": f"sha256:{package.content_sha256}"},
            "assessments": [],
        }

    digest = sha256_bytes(report.content)
    report_path = directory / "assessments" / assessor_id / f"{digest}.json"
    report_existed = report_path.exists()
    write_native_report(directory / "assessments" / assessor_id, report, root=boe_root)
    entry = {
        "path": f"assessments/{assessor_id}/{digest}.json",
        "sha256": f"sha256:{digest}",
    }
    if entry not in manifest["assessments"]:
        manifest["assessments"].append(entry)
    manifest["assessments"] = sorted(
        manifest["assessments"], key=lambda item: (item["path"], item["sha256"])
    )
    try:
        validate_boe_document(manifest)
        _atomic_write(
            manifest_path,
            (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode(),
            root=boe_root,
        )
    except AssessmentError:
        if not report_existed:
            report_path.unlink(missing_ok=True)
        raise
    return manifest_path


ACTIONABLE_FIELDS = (
    "severity",
    "category",
    "location",
    "finding",
    "text",
    "pattern",
    "confidence",
    "explanation",
    "remediation",
)


def _format_value(value: object) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def write_advice(
    output: Path,
    packages: list[SkillPackage],
    assessors: list[str],
    reports: list[tuple[SkillPackage, str, NativeReport]],
) -> None:
    report_entries: list[dict[str, str]] = []
    report_sections: list[str] = []
    finding_sections: list[str] = []
    for package, assessor_id, report in sorted(reports, key=lambda item: (item[0].name, item[1])):
        digest = write_native_report(output / "native" / assessor_id / package.name, report, root=output)
        relative = f"native/{assessor_id}/{package.name}/{digest}.json"
        report_entries.append(
            {
                "skill_name": package.name,
                "assessor_id": assessor_id,
                "path": relative,
                "sha256": f"sha256:{digest}",
            }
        )
        report_sections.append(f"- `{relative}` — `sha256:{digest}`")
        raw_findings = report.parsed.get("issues", report.parsed.get("findings", []))
        if isinstance(raw_findings, list):
            for index, finding in enumerate(raw_findings, start=1):
                if not isinstance(finding, dict):
                    continue
                fields = [(field, finding[field]) for field in ACTIONABLE_FIELDS if field in finding]
                if not fields:
                    continue
                finding_sections.append(f"### {package.name} / {assessor_id} / finding {index}")
                finding_sections.extend(f"- {field}: {_format_value(value)}" for field, value in fields)

    lines = [
        "# Skill Assessment Advice",
        "",
        "## Scope",
        "",
        f"- Skills: {', '.join(f'`{package.name}`' for package in packages)}",
        f"- Assessors: {', '.join(f'`{assessor}`' for assessor in assessors)}",
        "",
        "## Native Reports",
        "",
        *(report_sections or ["No native reports produced"]),
        "",
        "## Findings Summary",
        "",
        *(finding_sections or ["No summary produced"]),
        "",
    ]
    advice = "\n".join(lines).encode()
    _atomic_write(output / "advice.md", advice, root=output)
    manifest = {
        "schema_version": "skill-exchange-assessment-advice-artifacts/v1",
        "advice_path": "advice.md",
        "advice_sha256": f"sha256:{sha256_bytes(advice)}",
        "skills": [package.name for package in packages],
        "assessors": assessors,
        "native_reports": report_entries,
    }
    _atomic_write(
        output / "advice-manifest.json",
        (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode(),
        root=output,
    )
