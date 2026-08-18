from pathlib import Path
from zipfile import ZipFile

import pytest
from skill_exchange.models import SkillMetadata, SkillPackage
from skill_exchange.skills import hash_skill_package
from skill_exchange.zipper import write_skill_zip


def _skill_package(path: Path) -> SkillPackage:
    return SkillPackage(
        metadata=SkillMetadata(
            namespace="ai4sdlc",
            skill_id="sample-skill",
            name="sample-skill",
            description="Use for sample work.",
        ),
        path=path,
        skill_file=path / "SKILL.md",
        content_hash="hash",
    )


def test_skill_zip_places_skill_files_in_a_skill_directory(tmp_path: Path):
    skill_dir = tmp_path / "skills" / "ai4sdlc" / "sample-skill"
    (skill_dir / "references").mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Sample Skill\n")
    (skill_dir / "references" / "guide.md").write_text("# Guide\n")

    zip_path = write_skill_zip(_skill_package(skill_dir), tmp_path / "generated" / "zips")

    with ZipFile(zip_path) as archive:
        assert sorted(archive.namelist()) == [
            "sample-skill/SKILL.md",
            "sample-skill/references/guide.md",
        ]


def test_skill_zip_rejects_symlinks(tmp_path: Path):
    skill_dir = tmp_path / "skills" / "ai4sdlc" / "sample-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Sample Skill\n")
    outside = tmp_path / "outside.txt"
    outside.write_text("do not package\n")
    (skill_dir / "leak.txt").symlink_to(outside)

    with pytest.raises(ValueError, match="symlink"):
        write_skill_zip(_skill_package(skill_dir), tmp_path / "generated" / "zips")

    with pytest.raises(ValueError, match="symlink"):
        hash_skill_package(skill_dir)
