from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from .models import SkillPackage
from .skills import package_files


def write_skill_zip(skill: SkillPackage, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    zip_path = output_dir / f"{skill.metadata.namespace}--{skill.metadata.skill_id}.zip"
    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as archive:
        for path in package_files(skill.path):
            rel = path.relative_to(skill.path)
            archive.write(path, rel.as_posix())
    return zip_path
