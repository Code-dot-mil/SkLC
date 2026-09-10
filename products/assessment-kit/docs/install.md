# Install the assessment kit

Download these three assets for the same version from GitHub Releases:

- `assessment-kit-<version>.tar.gz`
- `assessment-kit-<version>.release-manifest.json`
- `assessment-kit-<version>.SHA256SUMS.txt`

Verify the downloads before extracting them:

```text
sha256sum --check assessment-kit-<version>.SHA256SUMS.txt
tar -xzf assessment-kit-<version>.tar.gz
cmp assessment-kit-<version>.release-manifest.json \
  assessment-kit-<version>/release-manifest.json
cd assessment-kit-<version>
sha256sum --check SHA256SUMS.txt
```

Create an isolated environment, install the wheel, and confirm the executable:

```text
python3 -m venv .venv
. .venv/bin/activate
python -m pip install dist/skill_assessment-*-py3-none-any.whl
skill-assessment --help
```

The archive contains exactly one wheel. For a prerelease, Python normalizes the
wheel's version segment (for example, release `1.2.3-rc.1` uses wheel version
`1.2.3rc1`). The release manifest records both forms.

Install NVIDIA [SkillSpector](https://github.com/NVIDIA/SkillSpector) at the
version and revision listed in `docs/assessor-configuration.md`. Put it on
`PATH` or set `SKILLSPECTOR_BIN` to the executable. SkillSpector and its own
dependencies are not bundled in the assessment-kit wheel.
