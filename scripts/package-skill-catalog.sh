#!/usr/bin/env bash
set -euo pipefail

# Package committed files only; run from the repository root.
output=${1:?Usage: bash scripts/package-skill-catalog.sh <archive.zip>}
[[ "$output" = /* ]] || output="$PWD/$output"
test ! -e "$output"
parent=$(dirname -- "$output")
mkdir -p "$parent"
stage=$(mktemp -d "$parent/.skill-catalog.XXXXXX")
trap 'rm -rf -- "$stage"' EXIT
skills=(python-secure-code-review unit-test-generation inline-documentation code-change-description)

mkdir "$stage/source" "$stage/product"
git -c core.autocrlf=false --work-tree="$stage/source" restore --source=HEAD --worktree -- \
  "${skills[@]/#/skills/ai4sdlc/}" products/skill-catalog/README.md
mv "$stage/source/skills/ai4sdlc" "$stage/product/skills"
mv "$stage/source/products/skill-catalog/README.md" "$stage/product/README.md"

(cd "$stage/product" && zip -qr "$output" .)
