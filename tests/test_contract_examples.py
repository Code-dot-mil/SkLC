from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath

from skill_exchange.frontmatter import parse_frontmatter

REPOSITORY_ROOT = Path(__file__).parents[1]
CONTRACTS_ROOT = REPOSITORY_ROOT / "contracts"


def test_boe_example_binds_skill_and_integrity_verified_native_report():
    example_root = CONTRACTS_ROOT / "boe" / "v1" / "examples"
    boe = json.loads((example_root / "boe.json").read_text())

    assert boe["schema_version"] == "skill-exchange-boe/v1"
    assert re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,62})", boe["skill"]["name"])
    assert re.fullmatch(r"sha256:[a-f0-9]{64}", boe["skill"]["content_sha256"])

    assert boe["assessments"]
    for assessment in boe["assessments"]:
        relative_path = PurePosixPath(assessment["path"])
        assert not relative_path.is_absolute()
        assert ".." not in relative_path.parts
        assert re.fullmatch(
            r"assessments/[a-z0-9](?:[a-z0-9-]{0,62})/[a-f0-9]{64}\.json",
            assessment["path"],
        )

        report_path = example_root.joinpath(*relative_path.parts)
        report_bytes = report_path.read_bytes()
        report_digest = hashlib.sha256(report_bytes).hexdigest()
        assert relative_path.stem == report_digest
        assert assessment["sha256"] == f"sha256:{report_digest}"

        report = json.loads(report_bytes)
        assert report["metadata"]["skillspector_version"]


def test_release_manifest_example_lists_installed_files_without_self_reference():
    contract_root = CONTRACTS_ROOT / "release-manifest" / "v1"
    manifest = json.loads((contract_root / "example.json").read_text())
    schema = json.loads((contract_root / "release-manifest.schema.json").read_text())
    path_pattern = re.compile(schema["$defs"]["relativePath"]["pattern"])

    paths = [artifact["path"] for artifact in manifest["artifacts"]]
    assert len(paths) == len(set(paths))
    assert all(path_pattern.fullmatch(path) for path in paths)
    containing_archive = f"{manifest['product']}-{manifest['version']}.tar.gz"
    assert containing_archive not in paths
    assert "release-manifest.json" not in paths
    assert "SHA256SUMS.txt" not in paths


def test_skill_package_example_uses_portable_standard_name():
    contract_root = CONTRACTS_ROOT / "skill-package" / "v1"
    metadata_schema = json.loads((contract_root / "metadata.schema.json").read_text())
    example = contract_root / "examples" / "example-review"
    frontmatter, _body = parse_frontmatter((example / "SKILL.md").read_text())

    name_rule = metadata_schema["properties"]["name"]
    assert name_rule["minLength"] <= len(frontmatter["name"]) <= name_rule["maxLength"]
    assert re.fullmatch(name_rule["pattern"], frontmatter["name"])
    assert frontmatter["name"] == example.name
    assert frontmatter["description"].strip()
