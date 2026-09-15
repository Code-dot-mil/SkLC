# Install the assessment kit

Prerequisites: Python 3.12 or newer, Git (to install the pinned assessor), and
`sha256sum`. Download these three assets for one version from GitHub Releases:

- `assessment-kit-<version>.tar.gz`
- `assessment-kit-<version>.release-manifest.json`
- `assessment-kit-<version>.SHA256SUMS.txt`

Set `VERSION` to the downloaded version, then verify before extraction:

```sh
: "${VERSION:?Set VERSION to the downloaded release version}"
sha256sum --check "assessment-kit-$VERSION.SHA256SUMS.txt"
tar -xzf "assessment-kit-$VERSION.tar.gz"
cmp "assessment-kit-$VERSION.release-manifest.json" \
  "assessment-kit-$VERSION/release-manifest.json"
cd "assessment-kit-$VERSION"
sha256sum --check SHA256SUMS.txt
```

Install the wheel and the supported NVIDIA
[SkillSpector](https://github.com/NVIDIA/SkillSpector) revision:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install dist/skill_assessment-*-py3-none-any.whl
python -m pip install 'skillspector @ git+https://github.com/NVIDIA/SkillSpector.git@e29b16d305b0e738e3d4b952ba102f5522a6f084'
skill-assessment --help
skillspector --version
```

The archive contains exactly one wheel. For a prerelease, Python normalizes the
wheel's version segment (for example, release `1.2.3-rc.1` uses wheel version
`1.2.3rc1`). The release manifest records both forms. SkillSpector and its
dependencies are installed separately from the assessment-kit wheel. An
existing compatible installation may instead be selected with `SKILLSPECTOR_BIN`.

For a first local proof, explicitly select static mode and use the shipped
example package. Run outside any source checkout; these commands need only the
extracted release, installed dependencies, and output directories:

```sh
export SKLC_SKILLSPECTOR_SCAN_MODE=static-only
skill=contracts/skill-package/v1/examples/example-review
skill-assessment validate --skill "$skill"
skill-assessment advise --skill "$skill" --assessor skillspector --output proof/advice
skill-assessment assess --skill "$skill" --assessor skillspector --boe-root proof/boe
skill-assessment verify-boe --skill "$skill" proof/boe/example-review
```

Retain `proof/advice` and `proof/boe` as the proof output. See
[assessor configuration](assessor-configuration.md) for the default LLM-assisted
mode and [generated files](generated-files.md) for the schema and checksum rules.
Offline dependency delivery is outside this release's scope.
