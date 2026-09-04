---
name: sklc-release-process
description: Prepare and execute a human-reviewed SkLC GitHub release after release automation is implemented. Use for release readiness, version recommendations, release notes, tags, artifacts, checksums, or GitHub Releases in this repository.
---

# SkLC Release Process

Follow `docs/specs/release-process.md` and the approved product specs. GitHub is
the maintainer source of truth and release origin. GitLab is a customer deployment
target, not the release origin.

## Confirmation boundary

Ask the user for confirmation immediately before every numbered release step.
Describe the exact action and any command or external change before asking. One
confirmation authorizes only that step; do not treat it as authorization for a
later step. This applies to read-only comparison of previous releases as well as
builds, commits, pushes, tags, GitHub Releases, and asset uploads.

Stop when a check fails or a required choice is unresolved. Never create or move
a tag, push a commit, create a GitHub Release, or upload an asset without the
confirmation for that exact step.

## Release steps

1. Confirm the release scope. Include every product that has reached its first
   releasable milestone and has supporting build and verification automation.
   Products share one SkLC version; they do not have separate version streams.
2. Confirm each included product has an approved current spec and no unresolved
   release blocker.
3. Confirm this skill exists and matches the approved release-process spec.
4. Compare the tag candidate with the previous GitHub release. Report only
   customer-, operator-, skill-user-, or catalog-maintainer-visible changes.
5. Propose and justify one SemVer bump: patch for compatible fixes or documentation,
   minor for backward-compatible capabilities or a newly releasable product, and
   major for a breaking artifact, contract, command, installation, or compatibility
   change. Ask the maintainer to accept or change it.
6. Draft a concise release-notes section headed `## <version>` for the accepted
   version. Exclude internal churn, formatting-only changes, non-behavioral
   refactors, and test-only changes unless they explain a user-visible fix. Ask
   the maintainer to accept or revise the text.
7. Append the accepted section to `RELEASE_NOTES.md`. Ask before editing it.
8. Commit and push the accepted release notes. Ask separately before the commit
   and before the push.
9. Build the release candidate from that commit without creating a tag. Ask
   before running the build. The two currently releasable artifacts are
   `deployment-kit-prebuilt-<version>.tar.gz` and
   `skill-catalog-<version>.tar.gz`.
10. Inspect each archive. Confirm its root name and required files, its internal
    `release-manifest.json` and `SHA256SUMS.txt`, required contracts and docs,
    and the absence of secrets, local paths, generated caches, maintainer-only
    files, or out-of-scope products.
11. Run the product tests and acceptance proofs. For the prebuilt deployment kit,
    prove an unchanged clean-project GitLab Pages deployment. For the skill
    catalog, prove the exact governed skill set, contract validation, checksum
    validation, and clean workspace skill discovery. Ask before each external
    proof or workflow execution.
12. Create and push the annotated tag `v<version>` on the commit containing the
    accepted notes. Ask before creating the tag and again before pushing it.
13. Monitor the tag-triggered GitHub Actions release workflow. It must create the
    two product archives, top-level `release-manifest.json`, and
    `SHA256SUMS.txt`; create the GitHub Release; use the accepted version section
    as the release body; and upload no separate release-notes asset.
14. Inspect the published GitHub Release and verify its description, asset names,
    manifests, and checksums. Ask before downloading or otherwise executing this
    verification.

Do not release `assessment-kit` or `deployment-kit-operator` until each has reached
its first releasable milestone and has supporting release automation.
