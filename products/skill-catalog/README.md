# Skill Catalog

This download contains these complete skill folders and their supporting files:

- `python-secure-code-review`: secure Python code review.
- `unit-test-generation`: unit test generation.
- `inline-documentation`: inline documentation.
- `code-change-description`: commit messages and pull request descriptions.

Download `skill-catalog-<version>.tar.gz` and its matching `.tar.gz.sha256` file
from [SkLC Releases](https://github.com/Code-dot-mil/SkLC/releases). Replace
`<version>` below with the downloaded version:

```sh
sha256sum --check skill-catalog-<version>.tar.gz.sha256
tar -xzf skill-catalog-<version>.tar.gz
```

Copy the complete skill folders from `skill-catalog/skills/` into your workspace's
`.agents/skills/`. Keep supporting files with each skill, and compare any existing
same-named folders before replacing them. Start a fresh agent session in that
workspace and confirm the skills appear in its available-skills list.

The CI `skill-catalog` artifact contains the same layout as `skill-catalog.tar.gz`
with its matching checksum. It is a test download, not a published release.
