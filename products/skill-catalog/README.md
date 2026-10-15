# Skill Catalog

This download contains these complete skill folders and their supporting files:

- `python-secure-code-review`: secure Python code review.
- `unit-test-generation`: unit test generation.
- `inline-documentation`: inline documentation.
- `code-change-description`: commit messages and pull request descriptions.

Download `skill-catalog-<version>.zip` from
[SkLC Releases](https://github.com/Code-dot-mil/SkLC/releases). Expand that asset's
details to see its `sha256:` digest. Replace `<version>` below with the downloaded
version and calculate its SHA-256:

```sh
sha256sum skill-catalog-<version>.zip
```

On macOS, use `shasum -a 256` in place of `sha256sum`. Compare the 64-character
result with GitHub's digest for that asset, ignoring the `sha256:` prefix. If they
differ, stop and download it again. Once they match, unzip once into a new folder:

```sh
unzip skill-catalog-<version>.zip -d skill-catalog
```

Copy the complete skill folders from `skill-catalog/skills/` into your workspace's
`.agents/skills/`. Keep supporting files with each skill, and compare any existing
same-named folders before replacing them. Start a fresh agent session in that
workspace and confirm the skills appear in its available-skills list.

The CI `skill-catalog.zip` download is also a single ZIP with `skills/` and `README.md`
at its root. Unzip it into `skill-catalog/` and install as above. It is a test
download, not a published release.
