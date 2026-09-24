#!/usr/bin/env bash
set -euo pipefail

# Package committed files only; run from the repository root.
archive=${1:?Usage: bash scripts/package-skill-catalog.sh <archive.tar.gz>}
[[ "$archive" = /* ]] || archive="$PWD/$archive"
test ! -e "$archive"
test ! -e "$archive.sha256"
output=$(dirname -- "$archive")
mkdir -p "$output"
stage=$(mktemp -d "$output/.skill-catalog.XXXXXX")
trap '[[ "$stage" == "$output"/.skill-catalog.* ]] && rm -rf -- "$stage"' EXIT
skills=(python-secure-code-review unit-test-generation inline-documentation code-change-description)

git -c core.autocrlf=false archive HEAD "${skills[@]/#/skills/ai4sdlc/}" products/skill-catalog/README.md |
  tar -xf - -C "$stage"
test -z "$(find "$stage" -type l -print -quit)"
mkdir "$stage/skill-catalog"
cp -R "$stage/skills/ai4sdlc" "$stage/skill-catalog/skills"
cp "$stage/products/skill-catalog/README.md" "$stage/skill-catalog/README.md"
for skill in "${skills[@]}"; do
  test -s "$stage/skill-catalog/skills/$skill/SKILL.md"
done

tar -czf "$archive" -C "$stage" skill-catalog
checksum=(sha256sum)
command -v sha256sum >/dev/null 2>&1 || checksum=(shasum -a 256)
(cd "$output" && "${checksum[@]}" "$(basename -- "$archive")" > "$(basename -- "$archive").sha256")
