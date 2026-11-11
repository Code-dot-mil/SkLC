# Release Notes

After the maintainer accepts a version and its notes, append a section headed `## <version>` here. Commit and push that section before creating the matching `v<version>` tag. Follow [the release process](CI.md#releases).

The workflow uses only that version's nonempty section as the GitHub Release description. Release notes are not uploaded as a separate asset. No release version or release notes have been accepted by adding this document.

## 1.3.0

- Add an optional manual assessment job for Operator merge requests, with guidance for configuring assessment access.
- Show release ancestry and localized build information on the site.
- Clarify scanner findings, risk ratings, and the role of human safety approval.
- Make assessment coverage enforcement an explicit option.
- Refresh the bundled skills’ assessment evidence.

## 1.2.0

- Include a readable assessment summary in each skill download and in the assessment bundle.
- Rename the skill catalog downloads to `skill-bundle-1.2.0.zip` and `skill-bundle-assessments-1.2.0.zip`. Update download automation that uses the previous `skill-catalog` filenames.
- Standardize Operator generated data at `.exchange/generated/` beside `site/`. Custom build scripts should use this location.
- Preserve skill creation and update dates from recorded source history instead of filesystem timestamps.

## 1.1.0

- Add the Operator deployment kit for building and hosting a customized exchange.
- Ship the standalone assessment CLI and catalog assessment evidence.
- Add assessment advice and adjudication workflows.
- Harden site sanitization and improve deployment guides.

## 1.0.0

First SkLC release, providing a prebuilt Skill Exchange site and a separate catalog of developer skills.

### Prebuilt Skill Exchange site

The Skill Exchange site lets users browse agent skills, read their review evidence and risk information, and download skill bundles. The deployment kit provides a ready-to-host copy of the site.

1. Download `deployment-kit-prebuilt-1.0.0.zip` from this release's assets and follow the [installation guide](https://github.com/Code-dot-mil/SkLC/blob/v1.0.0/products/deployment-kit/docs/prebuilt/install.md) to check and unpack it.
2. Follow the deployment guide for [GitLab Pages](https://github.com/Code-dot-mil/SkLC/blob/v1.0.0/products/deployment-kit/docs/prebuilt/deploy-gitlab-pages.md) or [another static host](https://github.com/Code-dot-mil/SkLC/blob/v1.0.0/products/deployment-kit/docs/prebuilt/deploy-static-hosting.md).

### Developer skill catalog

The skill catalog provides four skills for your coding agent: secure Python code review, unit test generation, inline documentation, and change descriptions. Each skill includes its instructions and supporting files.

1. Download `skill-catalog-1.0.0.zip` from this release's assets.
2. Follow the [catalog installation guide](https://github.com/Code-dot-mil/SkLC/blob/v1.0.0/products/skill-catalog/README.md) to check the download, install the skills in your workspace, and confirm your agent can find them.
