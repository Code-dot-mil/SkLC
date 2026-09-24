# Release Process Spec

## Decision baseline

This spec follows `docs/decisions.md`: GitHub is the maintainer source of truth and release origin; GitLab is the customer deployment environment; products remain standalone. This spec covers SkLC-managed release artifacts; skill lifecycle guidance is published from the Code-dot-mil AI4SDLC GitHub.

## Outcome

A maintainer can create a GitHub release containing every currently releasable SkLC product artifact after completing a human-reviewed release checklist.

## Status

Approved.

## Releasable products

The release process uses these product IDs and artifact names:

| Product ID | Artifact name |
|---|---|
| `deployment-kit-prebuilt` | `deployment-kit-prebuilt-<version>.tar.gz` |
| `skill-catalog` | `skill-catalog-<version>.tar.gz` |
| `assessment-kit` | `assessment-kit-<version>.tar.gz` |
| `deployment-kit-operator` | `deployment-kit-operator-<version>.tar.gz` |

Products and components are not individually versioned. `<version>` is the
single SkLC GitHub release version for every artifact included in that release.
Product IDs identify artifacts and checklist scope; they do not create separate
version streams.

A product becomes releasable when it has achieved its first roadmap milestone and
has supporting CI definitions for building and verifying its release artifact.
After that point, it remains part of every SkLC release. Releases do not offer a
product-selection step: each release contains every currently releasable product
artifact.

Early releases contain fewer artifacts only because not every product has reached
its first releasable state yet. Each releasable product artifact must remain
downloadable, verifiable, and usable independently.

## GitHub release flow

The basic release flow is manual tag creation plus a GitHub Actions workflow:

1. A maintainer identifies every product currently in a releasable state.
2. A maintainer completes the release checklist for each releasable product.
3. Codex compares the proposed release to the previous release, proposes a SemVer version bump with justification, and identifies the user-relevant changes for release notes.
4. A maintainer accepts or changes the version.
5. Codex drafts a concise release-notes section titled with the accepted version.
6. A maintainer reviews the release notes, commits them, and pushes them before creating the tag.
7. A maintainer creates the release tag on the commit that contains the accepted release notes.
8. GitHub Actions builds the releasable artifacts, creates shared `release-manifest.json` and `SHA256SUMS.txt`, creates the GitHub Release with that version's release-notes snippet as the release description, and uploads the archives and verification files. The manifest lists both archives and the catalog's adjacent `.tar.gz.sha256` file; `SHA256SUMS.txt` also covers the manifest.

`SHA256SUMS.txt` uses the standard checksum-file format:

```text
<64 lowercase hex sha256>  <filename>
```

## Release checklist

Before tagging, the maintainer works through this checklist in order:

1. Confirm every releasable product is included in the release.
2. Confirm each releasable product has a current approved spec and no unresolved release blocker.
3. Confirm the release-process skill exists at `.agents/skills/sklc-release-process/SKILL.md` and describes the known good path without session-specific discovery notes.
4. Ask Codex to compare the candidate release with the previous release and propose a SemVer bump with justification.
5. Review the proposed version against the releasable products' user-visible changes and accept or change the version.
6. Ask Codex to draft concise release notes for the accepted version. The notes include only changes useful to customers, operators, skill users, or catalog maintainers.
7. Append the accepted release notes to the repository's release notes or changelog document, using a heading that contains the accepted version.
8. Commit and push the release notes before creating the release tag.
9. Build each releasable product artifact from the tag candidate.
10. Confirm each product includes its documented contents and installation README. The prebuilt site includes its manifest, checksums, and required contracts. The skill catalog archive contains only its README and complete skill folders, with an adjacent archive checksum.
11. Run each releasable product's product-specific tests and acceptance proof.
12. For `deployment-kit-prebuilt`, confirm the artifact deploys unchanged to GitLab Pages from a clean GitLab project.
13. For `skill-catalog`, check its archive checksum and confirm the complete skill folders can be copied into workspace `.agents/skills/` and discovered in a fresh agent session.
14. Confirm no secrets, local paths, generated cache state, maintainer-only workflow details, or unpublished artifacts are included.
15. Create the release tag only after all checklist items above pass.
16. Confirm the GitHub Release description uses the accepted release-notes snippet for that version.
17. Confirm the uploaded assets match the product archives and verification files listed above, and that the shared manifest and checksums cover both products. Release notes are not uploaded as a separate asset.

## Codex release skill

The repository will provide a local Codex skill at `.agents/skills/sklc-release-process`. The skill is created inline while implementing the release-process issue, before using the process for an actual release. It must be standalone and describe the known good path that a fresh Codex session can follow for the next release. It must not mention session-specific false starts, wrong turns, or development-discovery history.

The skill guides Codex through the release checklist and release-note drafting. It must require Codex to ask the user before executing each release step, especially commands that build artifacts, inspect previous releases, create tags, push commits, create GitHub Releases, or upload release assets.

Creating the skill is implementation work for the release-process issue. It is
not itself a product release step, except that future releases confirm the skill
exists before using it.

## Release notes and version recommendation

Codex-assisted release notes compare the tag candidate to the previous release and include only changes that affect a customer, operator, skill user, or skill catalog maintainer. Internal churn, formatting-only edits, refactors without behavior change, and test-only changes are excluded unless they explain a user-visible fix.

Accepted release notes are committed and pushed before tagging. The GitHub Release uses the accepted notes for that version as the release description, through the GitHub web form, GitHub CLI release notes option, or Releases API `body` field. Release notes are not uploaded as a separate release asset.

Codex also suggests the SemVer bump:

- `patch` for compatible fixes or documentation corrections.
- `minor` for backward-compatible new product capabilities or newly releasable products.
- `major` for breaking changes to artifacts, contracts, commands, installation flow, or documented compatibility.

The maintainer makes the final version decision.

## Exclusions

- Fully automated release approval.
- Automatic tag creation without maintainer confirmation.
- Publishing products that have not completed their checklist.
- Release notes that summarize every commit.
