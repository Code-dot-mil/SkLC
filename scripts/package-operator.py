"""Assemble operator sources and the same release's catalog and assessment wheel."""

import argparse
import subprocess
from pathlib import Path, PurePosixPath
from zipfile import ZIP_DEFLATED, ZipFile

from skill_exchange.release import validate_version


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    validate_version(args.version)
    # The explicit source inventory excludes generated data, dependencies and maintainer workflows.
    roots = ["site/src", "site/scripts", "site/public/favicon.ico", "site/package.json",
             "site/package-lock.json", "site/astro.config.mjs", "site/tsconfig.json", "site/.npmrc",
             "scripts/skill_exchange", ".exchange/*.yaml", ".exchange/site-config.json", ".gitignore", "LICENSE"]
    tracked = subprocess.check_output(["git", "ls-files", "-z", "--", *roots]).decode().split("\0")
    files = {name: Path(name).read_bytes() for name in tracked if name and name != "scripts/skill_exchange/release.py"}
    files.update({
        ".gitlab-ci.yml": Path("products/deployment-kit/ci/gitlab/operator/.gitlab-ci.yml").read_bytes(),
        "ci/assessment.yml": Path("products/assessment-kit/ci/gitlab/profile.yml").read_bytes(),
        "README.md": Path("products/deployment-kit/docs/operator/README.md").read_bytes(),
        "docs/assessment-kit.md": Path("products/assessment-kit/README.md").read_bytes(),
        f"wheels/{args.wheel.name}": args.wheel.read_bytes(),
        "VERSION": (args.version + "\n").encode(),
    })
    with ZipFile(args.catalog) as catalog:
        for item in catalog.infolist():
            path = PurePosixPath(item.filename)
            if item.is_dir():
                continue
            if path.is_absolute() or ".." in path.parts:
                raise ValueError(f"Invalid catalog path: {item.filename}")
            if path.parts[0] == "skills":
                files[(PurePosixPath("skills/ai4sdlc") / path.relative_to("skills")).as_posix()] = catalog.read(item)
            elif item.filename == "README.md":
                files["docs/catalog.md"] = catalog.read(item)
            else:
                raise ValueError(f"Unexpected catalog member: {item.filename}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / f"deployment-kit-operator-{args.version}.zip"
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        for name, content in sorted(files.items()):
            archive.writestr(name, content)
    print(output)


if __name__ == "__main__":
    main()
