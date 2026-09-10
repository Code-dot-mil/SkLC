# Assessment Kit

The assessment kit is a standalone Python CLI for validating unpacked skill
packages, producing SkillSpector advice, retaining native assessment reports,
and maintaining BOE v1 manifests. It does not require the catalog, site, Git,
GitHub, or GitLab.

## Prerequisites

- Python 3.12 or newer.
- NVIDIA [SkillSpector](https://github.com/NVIDIA/SkillSpector) version
  `2.10.0`, source revision
  `e29b16d305b0e738e3d4b952ba102f5522a6f084`, available on `PATH` or through
  `SKILLSPECTOR_BIN`.
- LLM provider configuration for the default `llm-assisted` scan mode, or an
  explicit `static-only` configuration.

See `docs/install.md` for release installation, `docs/commands.md` for CLI
usage, `docs/assessor-configuration.md` for exact configuration rules, and
`docs/generated-files.md` for retained artifact layouts.

## Development

From the repository root, use `just lint` and `just test`. To build the
standalone wheel directly:

```text
python -m build --wheel --outdir <wheel-output> products/assessment-kit
```

Release assembly takes an explicit version, source revision, timestamp, wheel,
and output directory. The release workflow updates the version in a temporary
source copy before building, so the checkout remains unchanged. The assembler
does not infer release identity from the checkout:

```text
python products/assessment-kit/release_tools/build.py \
  --repository-root . \
  --version 0.1.0 \
  --source-revision <full-40-character-git-commit> \
  --created-at 2026-09-10T16:00:00Z \
  --wheel <wheel-output>/skill_assessment-0.1.0-py3-none-any.whl \
  --output-directory <release-output>
```
