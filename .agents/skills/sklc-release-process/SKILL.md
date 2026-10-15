---
name: sklc-release-process
description: Use when a maintainer asks to prepare or publish an SkLC release. Do not start a release when asked only to implement or review release tooling.
---

# SkLC release process

GitHub is the release origin. Every release includes two independent product
ZIPs under one SemVer version:

- `deployment-kit-prebuilt-<version>.zip`
- `skill-catalog-<version>.zip`

GitHub computes and displays each asset's SHA-256 digest. A consumer chooses one
ZIP, compares its SHA-256 with that asset's GitHub digest, unzips once, and uses
it. All paths below are relative to the repository root.

## Prepare a reviewable candidate

When asked to release, read `AGENTS.md`, `CI.md`, `.github/workflows/release.yml`,
and the product installation guides. Confirm the remote is `Code-dot-mil/SkLC`
and identify the candidate commit. Preserve unrelated work.

Compare the candidate with the previous release and recommend a SemVer version
based on consumer impact. Agree on the version and release notes with the
maintainer. Use the version without `v` in filenames and the exact heading
`## <version>` in `RELEASE_NOTES.md`; the tag is `v<version>`. Keep notes focused
on changes consumers need to understand.

Select the intended release commit from GitHub and record its full SHA. Run the
readiness command from the candidate checkout, supplying the SHA selected from
GitHub rather than deriving it from local `HEAD`. See `CI.md` for authentication.

```sh
uv run --group release python -m skill_exchange.release check-ready \
  --version <version> --expected-commit <expected-commit-sha>
```

Treat the command as the release readiness gate. On success, report its candidate
SHA and CI run URL and proceed with the publication steps. On failure, report the
blocker and resolve it before tagging. Do not independently repeat its checks,
inspect its implementation, or reproduce CI locally as part of a routine release.
If the candidate changes, run the gate with the newly selected SHA. Do not run
assessments or alter tracked BOE to make a release pass.

Use the `static-site` and `skill-catalog.zip` artifacts from the verified CI run for
package previews and smoke testing.

Follow the shipped guides to try the candidate: serve the site's `public/` at the
intended host and try a skill download, or copy the catalog's skill folders into
a workspace and confirm discovery in a fresh agent session. For GitLab Pages,
configure `PAGES_RUNNER_TAG` and an approved `PAGES_IMAGE` if needed. Its job
publishes `public/` directly. Obtain approval before making external changes to
a customer project.

## Publish the agreed release

Present the exact candidate, version, notes, check results, and any blockers.
Obtain approval for commits, pushes, and publication unless already authorized
in the session. Follow the repository's PR and branch protection rules. Ensure
the tag targets the exact candidate SHA reported by the readiness command.

Before pushing `v<version>`, explain that the tag push starts the release workflow:
it checks the repository, builds the site, packages both products, and creates the
GitHub Release with the accepted notes and exactly the two archives above.
A tag push requires authorization for those publishing effects. Do not invoke
`gh release create` separately alongside the workflow.

After publication, inspect the Actions result and release: confirm its commit,
version, notes, prerelease status, and two assets. Download the needed product,
compare its SHA-256 with GitHub's digest once, unzip once, and follow its guide.
Report publication and any deployment results. On failure, describe the blocker
and agree on recovery before moving tags or replacing a published release.
