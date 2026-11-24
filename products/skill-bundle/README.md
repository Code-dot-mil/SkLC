# Skill Bundle

This download contains these complete skill folders and their supporting files:

- `python-secure-code-review`: secure Python code review.
- `unit-test-generation`: unit test generation.
- `inline-documentation`: inline documentation.
- `code-change-description`: commit messages and pull request descriptions.

To choose a skill and read its assessment, see [Choose and download a SkLC skill](https://github.com/Code-dot-mil/SkLC/blob/main/docs/using-skills.md). You need an agent that supports skills. Check its documentation for the installation location.

## Released product

Download `skill-bundle-<version>.zip` from [SkLC Releases](https://github.com/Code-dot-mil/SkLC/releases). Expand the asset details to see its `sha256:` digest. Run the command for your operating system in the download folder, replacing `<version>` with the downloaded version.

On Linux, use:

```sh
sha256sum "skill-bundle-<version>.zip"
```

On macOS, use:

```sh
shasum -a 256 "skill-bundle-<version>.zip"
```

On Windows (PowerShell), use:

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath "skill-bundle-<version>.zip"
```

Compare the 64-character result with GitHub's digest for that asset, ignoring letter case and the `sha256:` prefix. If they differ, download the file again. Once they match, extract the archive into a new folder.

On Linux or macOS, use:

```sh
unzip "skill-bundle-<version>.zip" -d skill-bundle
```

On Windows (PowerShell), use:

```powershell
Expand-Archive -LiteralPath "skill-bundle-<version>.zip" -DestinationPath "skill-bundle"
```

Copy the complete skill folders from `skill-bundle/skills/` to the location your agent uses. For example, some agents load skills from `.agents/skills/` at the top level of the project repository. If you use a project-level location, your team can review and version the installed skills with the project. Keep supporting files with each skill and compare any existing same-named folders before replacing them. Start a fresh agent session and confirm the skills appear in its available-skills list.

To read the assessment results for these skills, download the `skill-bundle-assessments` ZIP from the same release and follow the [assessment results guide](https://github.com/Code-dot-mil/SkLC/blob/main/products/skill-bundle-assessments/README.md).
