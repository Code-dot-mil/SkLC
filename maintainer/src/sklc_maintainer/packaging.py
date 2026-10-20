"""Assemble product downloads from one committed source snapshot and explicit build inputs."""

import argparse
import io
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path, PurePosixPath
from zipfile import ZIP_DEFLATED, ZipFile

from .release import validate_version


def catalog_selection(source: Path) -> dict[str, Path]:
    skills = {}
    for skill_file in sorted((source / "products/skill-catalog").glob("*/SKILL.md")):
        name = skill_file.parent.name
        skills[name] = skill_file.parent
    if not skills:
        raise ValueError("Committed catalog contains no skills")
    return skills


def write_zip(output: Path, files: dict[str, bytes]) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        for name, content in sorted(files.items()):
            archive.writestr(name, content)
    return output


def package_catalog(source: Path, output: Path) -> Path:
    if output.exists():
        raise FileExistsError(output)
    files = {"README.md": (source / "products/skill-catalog/README.md").read_bytes()}
    for name, directory in catalog_selection(source).items():
        for path in directory.rglob("*"):
            if path.is_symlink():
                raise ValueError(f"Skill package must not contain symlinks: {path}")
            if path.is_file():
                files[f"skills/{name}/{path.relative_to(directory).as_posix()}"] = path.read_bytes()
    return write_zip(output, files)


def package_assessments(source: Path, output: Path, source_dir: Path | None) -> Path:
    if output.exists():
        raise FileExistsError(output)
    committed = source / "products/skill-catalog-assessments"
    reports = committed if source_dir is None else source_dir
    files = {"README.md": (committed / "README.md").read_bytes()}
    for name in catalog_selection(source):
        for filename in ("skillspector.json", "adjudication.json"):
            report = reports / name / filename
            if any(path.is_symlink() for path in (reports, report.parent, report)) or not report.is_file():
                raise ValueError(f"Missing or symlinked report: {report}")
            files[f"{name}/{filename}"] = report.read_bytes()
    return write_zip(output, files)


def checked_path(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or "\\" in name:
        raise ValueError(f"Invalid catalog path: {name}")
    return path


def package_operator(source: Path, catalog_path: Path, assessments_path: Path,
                     wheel: Path, output_dir: Path, version: str) -> Path:
    from skill_assessment.hashing import skill_digest
    from skill_assessment.reports import is_current_assessment

    operator = source / "products/deployment-kit"
    roots = {source / "site" / name: f"site/{name}" for name in (
        "src", "scripts", "public/favicon.ico", "package.json", "package-lock.json",
        "astro.config.mjs", "tsconfig.json", ".npmrc",
    )}
    roots.update({operator / "src": "src", operator / "pyproject.toml": "pyproject.toml"})
    files = {}
    for root, destination in roots.items():
        if not root.exists():
            raise ValueError(f"Missing committed product source: {root}")
        paths = list(root.rglob("*")) if root.is_dir() else [root]
        for path in paths:
            if path.is_file():
                suffix = path.relative_to(root).as_posix() if root.is_dir() else ""
                files[f"{destination}/{suffix}".rstrip("/")] = path.read_bytes()
    assets = source / "products/deployment-kit"
    files.update({
        ".gitlab-ci.yml": (assets / "ci/gitlab/operator/.gitlab-ci.yml").read_bytes(),
        "ci/assessment.yml": (assets / "ci/gitlab/operator/assessment.yml").read_bytes(),
        "README.md": (assets / "docs/operator/README.md").read_bytes()
        .replace(b"../../containers/assessment/README.md", b"assessment/container/README.md")
        .replace(b"../../../assessment-kit/README.md", b"assessment/README.md"),
        "ci/configure_runtime_trust.py": (assets / "ci/gitlab/operator/configure_runtime_trust.py").read_bytes(),
        "assessment/README.md": (source / "products/assessment-kit/README.md").read_bytes(),
        f"assessment/{wheel.name}": wheel.read_bytes(),
        "assessment/requirements.txt": f"./assessment/{wheel.name}\n".encode(),
        "VERSION": (version + "\n").encode(),
        ".gitignore": (operator / ".gitignore").read_bytes(),
    })
    for name in ("Dockerfile", ".dockerignore", "README.md"):
        content = (assets / "containers/assessment" / name).read_bytes()
        files[f"assessment/container/{name}"] = content.replace(
            b"../../../assessment-kit/README.md", b"../README.md",
        )
    names = set()
    with ZipFile(catalog_path) as catalog:
        for item in catalog.infolist():
            path = checked_path(item.filename)
            if item.is_dir():
                continue
            if path.parts[0] == "skills" and len(path.parts) > 2:
                names.add(path.parts[1])
                files[f"upstream/skills/{path.relative_to('skills')}"] = catalog.read(item)
            elif item.filename == "README.md":
                files["upstream/catalog.md"] = catalog.read(item)
            else:
                raise ValueError(f"Unexpected catalog member: {item.filename}")
    if not names:
        raise ValueError("Catalog archive contains no upstream skills")
    with ZipFile(assessments_path) as assessments:
        for name in sorted(names):
            for report in ("skillspector.json", "adjudication.json"):
                files[f"upstream/evidence/{name}/{report}"] = assessments.read(f"{name}/{report}")
    with tempfile.TemporaryDirectory(prefix="sklc-operator-") as temporary:
        stage = Path(temporary)
        for name, content in files.items():
            if name.startswith("upstream/"):
                destination = stage / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(content)
        for name in names:
            evidence = stage / "upstream/evidence" / name
            digest = skill_digest(stage / "upstream/skills" / name)
            if not is_current_assessment(evidence, digest, static_only=False):
                raise ValueError(f"Upstream assessment is not current: {name}")
    return write_zip(output_dir / f"deployment-kit-operator-{version}.zip", files)


def stage_prebuilt(source: Path, site_dir: Path, output: Path) -> Path:
    shutil.copytree(site_dir, output / "public")
    (output / "public/.gitkeep").unlink(missing_ok=True)
    prebuilt = source / "products/deployment-kit"
    shutil.copy2(prebuilt / "ci/gitlab/prebuilt/.gitlab-ci.yml", output / ".gitlab-ci.yml")
    shutil.copy2(prebuilt / "docs/prebuilt/README.md", output / "README.md")
    (output / "docs").mkdir()
    for name in ("install.md", "deploy-gitlab-pages.md", "deploy-static-hosting.md"):
        shutil.copy2(prebuilt / "docs/prebuilt" / name, output / "docs" / name)
    return output


def package_prebuilt(source: Path, site_dir: Path, output_dir: Path, version: str) -> Path:
    with tempfile.TemporaryDirectory(prefix="sklc-prebuilt-") as temporary:
        staged = stage_prebuilt(source, site_dir, Path(temporary) / "prebuilt")
        output_dir.mkdir(parents=True, exist_ok=True)
        output = output_dir / f"deployment-kit-prebuilt-{version}"
        return Path(shutil.make_archive(str(output), "zip", root_dir=staged))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("catalog", "assessments", "operator", "prebuilt"):
        command = commands.add_parser(name)
        command.add_argument("--repo-root", type=Path, default=Path.cwd())
        if name in {"catalog", "assessments"}:
            command.add_argument("--output", type=Path, required=True)
        else:
            command.add_argument("--output-dir", type=Path, required=True)
        if name == "assessments":
            command.add_argument("--source-dir", type=Path)
        if name == "operator":
            for option in ("catalog", "assessments", "wheel"):
                command.add_argument(f"--{option}", type=Path, required=True)
            command.add_argument("--version", required=True)
        if name == "prebuilt":
            mode = command.add_mutually_exclusive_group(required=True)
            mode.add_argument("--version")
            mode.add_argument("--stage", action="store_true")
            command.add_argument("--site-dir", type=Path,
                                 default=Path("site/dist"))
    args = parser.parse_args()
    if getattr(args, "version", None) is not None:
        validate_version(args.version)
    revision = subprocess.check_output(["git", "-C", str(args.repo_root), "rev-parse", "HEAD"], text=True).strip()
    committed = subprocess.check_output([
        "git", "-C", str(args.repo_root), "archive", "--format=tar", revision, "products", "site",
    ])
    with tempfile.TemporaryDirectory(prefix="sklc-source-") as temporary:
        source = Path(temporary)
        with tarfile.open(fileobj=io.BytesIO(committed)) as archive:
            archive.extractall(source, filter="data")
        if args.command == "catalog":
            output = package_catalog(source, args.output)
        elif args.command == "assessments":
            output = package_assessments(source, args.output, args.source_dir)
        elif args.command == "operator":
            output = package_operator(source, args.catalog, args.assessments, args.wheel, args.output_dir, args.version)
        else:
            site = args.site_dir if args.site_dir.is_absolute() else args.repo_root / args.site_dir
            if args.stage:
                output = stage_prebuilt(source, site, args.output_dir)
            else:
                output = package_prebuilt(source, site, args.output_dir, args.version)
    print(output)


if __name__ == "__main__":
    main()
