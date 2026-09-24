---
name: sklc-release-process
description: Guide a maintainer through an SkLC release, including readiness checks, SemVer recommendation, accepted release notes, and manual-tag GitHub publication. Require confirmation before each release step. Do not start a release when asked only to implement or review release tooling.
---

# SkLC release process

Follow the approved `docs/specs/release-process.md`. GitHub is the release
origin; customers receive standalone artifacts, not the maintainer source tree.
All repository paths below are relative to the SkLC repository root.

## Confirmation rule

Creating, editing, or reviewing this skill is implementation work, not permission
to release. When asked to perform a release, first ask permission for step 1;
do not start inspecting releases or running release commands before that answer.

Before **each numbered step**, state what you will do, the exact target and
commands where applicable, the expected result, and any external effects. Ask
for explicit confirmation and wait. Perform only that approved step, report
what happened and what passed or failed, then ask before the next step. This
also applies to read-only release inspection, builds, checks, and retries.
An approval to plan, review, or proceed with one step does not approve later
commits, pushes, tags, deployments, releases, or uploads.

The tag push triggers non-interactive GitHub Actions. Before that push, obtain
explicit approval for its entire automatic sequence: build, verify, create the
GitHub Release, and upload assets. Do not promise interactive pauses inside
Actions or independently run its publishing command.

On a failed check, missing prerequisite, changed candidate, conflicting spec,
or unavailable approval, stop the release and explain the next decision needed.
Do not bypass verification, generate replacement evidence, force-push, move a
tag, overwrite a release, or retry publication without a separately approved
recovery plan.

## Release steps

1. **Inspect the release context and readiness.** After confirmation, locate the
   repository with `git rev-parse --show-toplevel`, confirm the remote targets
   `Code-dot-mil/SkLC`, and inspect the branch, commit, and worktree status. Read
   `AGENTS.md`, the approved `docs/specs/release-process.md` from GitHub `main`,
   `docs/roadmap.md`, the relevant product specs, `CI.md`, and
   `.github/workflows/release.yml`. Compare the candidate's release spec with
   approved `main` without switching or changing the worktree. Report unavailable
   remote information as unverified, not as approval. Preserve existing changes;
   require a clean, identified candidate before building or tagging.

   Identify **every currently releasable product**, its approved spec, build and
   verification path, acceptance evidence, and unresolved blockers. There is one
   SkLC version for all included artifacts, no per-product versioning, and no
   product-selection menu. Once a product is releasable it remains in subsequent
   releases. Confirm this skill exists and required tooling/access is available.

   The current workflow supports `deployment-kit-prebuilt` and the
   `skill-catalog` download. `assessment-kit` and `deployment-kit-operator`
   remain outside this implementation. If another product is now releasable, stop for
   the necessary release-tooling update; do not silently omit it or assemble it
   ad hoc. Missing acceptance proof is still a release blocker, not evidence
   that the prebuilt product is ready.

2. **Compare with the previous release.** Ask before inspecting GitHub releases,
   tags, diffs, or prior assets. Identify the previous applicable release and
   its commit, then compare it with the candidate, including customer-facing
   content, artifact layout, contracts, dependencies, and installation behavior.
   If no previous release exists, say this is the first release and assess the
   candidate against its approved specs; do not invent a prior version.

3. **Recommend and agree on the version.** Ask before preparing the recommendation.
   Propose a SemVer bump with customer-facing justification: patch for compatible
   fixes/docs, minor for backward-compatible capabilities or newly releasable
   products, major for breaking artifact, contract, command, installation, or
   compatibility changes. The maintainer accepts or changes the version. Use
   that exact version without `v` in notes and filenames, and `v<version>` for
   the tag. Do not select an initial version or prerelease status on their behalf.

4. **Draft release notes.** Ask before drafting concise notes for the accepted
   version. Include only changes useful to customers, operators, skill users, or
   catalog maintainers; omit internal churn and test-only changes unless needed
   to explain a user-visible fix. Show a section headed exactly `## <version>`
   and wait for the maintainer to accept or revise the text.

5. **Append accepted notes.** Ask before editing `RELEASE_NOTES.md`. Append only
   the accepted version-specific section, preserving prior notes. There must be
   exactly one nonempty section with that heading. Validate the accepted version
   with `uv run python -m skill_exchange.release validate-version --version
   <version>` and preview the actual release body with the `release-notes`
   subcommand, supplying `--version <version> --notes-file RELEASE_NOTES.md
   --output <temporary-body-file>`. These are command templates: replace the
   version and choose a new temporary output path before proposing execution.
   Set `PYTHONPATH` to `scripts` in the repository root. The body is a preview,
   not an additional release asset.

6. **Commit the notes.** Ask before staging the accepted notes and committing
   them. Show the exact diff and intended branch first; do not include unrelated
   changes or use a blanket add. Record the resulting candidate commit.

7. **Push the notes commit.** Ask separately before pushing the agreed branch to
   the confirmed GitHub remote. Follow the repository's required PR/merge checks;
   do not bypass branch protection. If merging changes the candidate commit,
   identify the resulting commit and revalidate before continuing. Notes must
   be committed and pushed before any release tag is created.

8. **Build the candidate artifacts.** Ask before installing dependencies or
   building. Use an isolated checkout of the identified candidate and a fresh
   temporary output directory. Use Python 3.12, Node.js 22, `uv`, and the exact
   dependency installation, Python checks, site checks, exchange generation,
   and site build commands in `.github/workflows/release.yml`; do not execute
   its tag-trigger or publishing steps locally.

   Set `PYTHONPATH=scripts`, `SKILL_EXCHANGE_SOURCE_REPOSITORY_URL` to the
   confirmed GitHub repository URL, and `SKILL_EXCHANGE_SOURCE_BRANCH` to the
   candidate commit. Run `publish-local` with `--scan-mode static-only
   --reuse-boe-only`: this reuses successful exact-content tracked BOE and must
   fail if evidence is missing. Do not invoke Skillspector or an LLM, remove
   `--reuse-boe-only`, or alter tracked BOE to make a release pass. Python
   produces exchange data; the Node build only consumes it.

   First package the four committed skill folders with `bash scripts/package-skill-catalog.sh
   <temporary-assets-directory>/skill-catalog-<version>.tar.gz`. This produces the
   archive and its adjacent `.sha256` file without running assessments or site tooling.

   Package the built `site/dist` using `uv run python -m skill_exchange.release
   build --repo-root . --site-dir site/dist --version <version>
   --source-revision <candidate-commit> --output-dir <temporary-assets-directory>
   --catalog-archive <temporary-assets-directory>/skill-catalog-<version>.tar.gz`.
   Replace every template value with the approved value before execution. Set
   `SOURCE_DATE_EPOCH` to the candidate's commit timestamp, as the workflow does.
   Keep derived data, caches, previews, and artifacts out of the source worktree.

9. **Verify the extracted artifacts.** Ask before checking external
   `SHA256SUMS.txt`, extracting into a new directory, and running the shipped
   verifier from the extracted package root:
   `python3 -I -S scripts/verify_prebuilt.py . --expected-version <version>`.
   Use the accepted version. Run the same required-content checks as the release
   workflow. Confirm the archive contains `README.md`, all three product guides,
   deployment-only `.gitlab-ci.yml`, the vendored release-manifest schema,
   `scripts/verify_prebuilt.py`, the unchanged site under `public/`, internal
   manifest/checksums, and every referenced download. Review for secrets, local
   paths, generated caches, maintainer-only files, and unpublished artifacts.
   Verification failures block tagging; never edit checksums to conceal them.

   Check the catalog's `.tar.gz.sha256`, extract it, and follow its README to copy
   the complete skill folders into a clean workspace. Confirm discovery in
   a fresh agent session. The catalog has no separate manifest or verifier.
   Confirm the shared release manifest lists both archives and the catalog checksum,
   and that `SHA256SUMS.txt` verifies those assets and the shared manifest.

10. **Prove candidate deployment.** Ask before using a clean GitLab project,
    changing its configuration, or committing/pushing the extracted package.
    Agree on the project and available runner; keep `PAGES_RUNNER_TAG`
    configurable and confirm that the runner supports and can pull the selected
    `PYTHON_IMAGE`, which must provide a POSIX shell and Python 3.12+.
    Follow the package's `docs/install.md` and `docs/deploy-gitlab-pages.md`.
    Require the shipped `pages` job to verify and publish unchanged `public/`,
    without a customer build, assessment, catalog assembly, or input download.
    Record the candidate commit, archive/checksum, pipeline/job URL, and Pages
    URL; confirm the home page, styling, skill detail page, and download work.
    Obtain separate confirmation before each external mutation described in the
    deployment guide. Local verification does not prove GitLab deployment.

11. **Confirm the final release gate.** Ask to review every applicable item in
    the release-process spec's checklist with the maintainer. Confirm accepted
    notes are on the pushed candidate, required CI and artifact checks passed,
    deployment evidence is present, and no blocker remains. Verify that the
    candidate still matches the tested commit and that the intended tag/release
    does not already exist. Any candidate change invalidates earlier readiness
    evidence until the affected checks are repeated with approval.

12. **Create the local release tag.** Ask before creating exactly `v<version>`
    on the approved, pushed candidate commit. Show the commit and accepted notes
    first. Do not tag a moving branch implicitly or replace an existing tag.

13. **Push the release tag and authorize publication.** Ask separately before
    pushing that exact tag to the confirmed GitHub remote. Explain that the
    push starts `.github/workflows/release.yml`, which builds and verifies the
    package, generates external metadata/checksums, creates the GitHub Release
    using the accepted notes, and uploads exactly:

    - `deployment-kit-prebuilt-<version>.tar.gz`
    - `release-manifest.json`
    - `SHA256SUMS.txt`
    - `skill-catalog-<version>.tar.gz`
    - `skill-catalog-<version>.tar.gz.sha256`

    Release notes are the description, never a separate uploaded asset. Obtain
    explicit approval for these automatic effects before the tag push; do not
    run `gh release create` or upload assets manually alongside the workflow.

14. **Verify the published release.** Ask before inspecting the tag's Actions
    run and GitHub Release or downloading assets. Confirm the workflow succeeded,
    the release points to the approved commit, the description matches the
    extracted accepted snippet, prerelease status matches the accepted version,
    and exactly the expected assets exist. Download to a new temporary directory,
    check external checksums and manifest asset entries, then extract and run
    the included verifier again. A failed/partial workflow is not a successful
    release; stop and request a recovery decision rather than overwriting it.

15. **Record published-package acceptance and finish.** Ask before testing the
    downloaded GitHub Release package in a clean GitLab project using the shipped
    instructions, with separate approvals for external changes. Record the
    release tag, archive filename, passing `pages` pipeline/job evidence and
    served Pages URL, as required by `docs/specs/prebuilt-reference-site.md`.
    Candidate deployment proof alone does not complete this published-artifact
    acceptance check. Report publication and customer deployment as separate
    outcomes, with any outstanding blockers. Ask before removing only identified
    temporary files/worktrees created for this release; preserve tracked BOE and
    the acceptance record. Do not start another release automatically.
