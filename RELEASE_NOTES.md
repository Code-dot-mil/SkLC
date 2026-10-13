# Release Notes

After the maintainer accepts a version and its notes, append a section headed
`## <version>` here. Commit and push that section before creating the matching
`v<version>` tag. Follow [the release process](CI.md#releases).

The workflow uses only that version's nonempty section as the GitHub Release
description. Release notes are not uploaded as a separate asset. No release
version or release notes have been accepted by adding this document.

## 1.0.0

First SkLC release, providing a prebuilt Skill Exchange site and a separate
catalog of developer skills.

- Deploy the static Skill Exchange site to GitLab Pages or another static host.
  The package includes skill detail pages, review evidence, risk information,
  downloadable skill bundles, and installation and deployment guides.
- Verify the prebuilt package offline using its included Python verifier,
  manifest, and SHA-256 checksums. The included GitLab Pages job verifies the
  package before publishing the existing site without rebuilding it.
- Install four complete developer skills from the separate catalog archive:
  secure Python code review, unit test generation, inline documentation, and
  commit message and pull request description generation.
- Serve the static site at a domain root or beneath a URL path prefix.
- Read scan and update timestamps consistently in UTC across the catalog and
  skill pages, regardless of browser locale or timezone.

Prebuilt verification requires Python 3.12 or newer. GitLab Pages deployment
requires a Linux runner that supports job images and can pull the configured
Python image. Runner routing and image settings use CI/CD variables.

This release includes the prebuilt deployment kit and skill catalog. Assessment
tooling, operator site-build tooling, and managed updates are not included.
The catalog contains skill instructions and supporting files; separate catalog
assessment-evidence downloads are not included.
