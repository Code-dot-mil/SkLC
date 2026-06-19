from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from .models import SkillPackage


def write_skill_zip(skill: SkillPackage, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    zip_path = output_dir / f"{skill.metadata.namespace}--{skill.metadata.skill_id}.zip"
    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as archive:
        for path in sorted(p for p in skill.path.rglob("*") if p.is_file()):
            rel = Path(skill.metadata.namespace) / skill.metadata.skill_id / path.relative_to(skill.path)
            archive.write(path, rel.as_posix())
    return zip_path
