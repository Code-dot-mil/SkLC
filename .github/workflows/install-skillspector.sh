#!/usr/bin/env bash
set -euo pipefail

# CI supplies the external scanner without adding it to assessment-kit dependencies.
required=(SKILLSPECTOR_PROVIDER SKILLSPECTOR_MODEL AZURE_OPENAI_ENDPOINT
  AZURE_OPENAI_API_KEY AZURE_OPENAI_DEPLOYMENT AZURE_OPENAI_API_VERSION LLM_REQUESTS_PER_SECOND
  LLM_MAX_OUTPUT_TOKENS ASSESSMENT_TIMEOUT_SECONDS SSL_CERT_FILE)
for name in "${required[@]}"; do
  if [[ -z "${!name:-}" ]]; then
    echo "::error::Required assessment configuration is missing: $name"
    exit 1
  fi
done
test -r "$SSL_CERT_FILE"
export GIT_SSL_CAINFO="$SSL_CERT_FILE"
test "$SKILLSPECTOR_PROVIDER" = azure_openai

runtime="$RUNNER_TEMP/skillspector-runtime"
uv venv --clear --python "$(command -v python)" "$runtime"
uv pip install --python "$runtime/bin/python" \
  'skillspector @ git+https://github.com/NVIDIA/SkillSpector.git@e29b16d305b0e738e3d4b952ba102f5522a6f084'

# Keep the scanner's interpreter separate from uv's assessment-kit environment.
mkdir -p "$runtime/launcher"
printf '#!/bin/sh\nexec "%s" "%s" "$@"\n' \
  "$runtime/bin/python" "$GITHUB_WORKSPACE/.github/workflows/skillspector_runner.py" \
  > "$runtime/launcher/skillspector"
chmod +x "$runtime/launcher/skillspector"
echo "$runtime/launcher" >> "$GITHUB_PATH"
"$runtime/launcher/skillspector" --version
