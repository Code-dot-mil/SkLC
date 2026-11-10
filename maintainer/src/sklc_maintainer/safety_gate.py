"""Require safe determinations for the upstream catalog after generation."""

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, required=True)
    args = parser.parse_args()
    index = json.loads(args.index.read_text(encoding="utf-8"))
    skills = index["skills"]
    if not skills:
        parser.exit(1, "Safety gate failed: catalog has no skills.\n")
    failures = []
    for skill in skills:
        if skill.get("recommendation") != "SAFE":
            summary = skill.get("adjudication", {}).get("summary", "No adjudication summary")
            failures.append(f"{skill['skill_id']}: {skill.get('recommendation', 'missing')} — {summary}")
    if failures:
        parser.exit(1, "Safety gate failed:\n" + "\n".join(failures) + "\n")
    print(f"Safety gate passed: all {len(skills)} catalog skills are Safe to use.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
