---
name: sklc-release-process
description: Use when asked whether SkLC is ready for a release, to prepare a release, create a draft, or publish. Read before release checks or a general project review. Implementing or reviewing release tooling alone does not authorize a release.
---

# SkLC release process

GitHub is the release origin. The tag workflow owns packaging and draft creation;
the maintainer publishes that existing draft. Every release includes four
product artifacts under one SemVer version:

- `deployment-kit-prebuilt-<version>.zip`
- `deployment-kit-operator-<version>.zip`
- `skill-catalog-<version>.zip`
- `skill_assessment-<version>-py3-none-any.whl`

GitHub computes and displays each asset's SHA-256 digest. A consumer chooses a
product, compares its SHA-256 with that asset's GitHub digest, then unzips the ZIP
or installs the wheel. All paths below are relative to the repository root.

## Check readiness

Read this skill first for readiness, draft, and publication requests. Then read
`CI.md` and `.github/workflows/release.yml`. Confirm the remote is
`Code-dot-mil/SkLC` and identify the candidate commit. Preserve unrelated work.

Compare the candidate with the previous release and recommend a SemVer version
based on consumer impact. Agree on the version and release notes with the
maintainer. Use the version without `v` in filenames and the exact heading
`## <version>` in `RELEASE_NOTES.md`; the tag is `v<version>`. Keep notes focused
on changes consumers need to understand. Set the assessment-kit version in
`products/assessment-kit/pyproject.toml` to match the release under Python packaging
normalization before selecting the candidate. The workflow builds the wheel with
`uv build` and uploads it alongside the ZIPs.

Select the intended release commit from GitHub and record its full SHA. Run the
readiness command from the candidate checkout, supplying the SHA selected from
GitHub rather than deriving it from local `HEAD`. See `CI.md` for authentication.

```sh
uv run --group release python -m sklc_maintainer.release check-ready \
  --version <version> --expected-commit <expected-commit-sha>
```

Treat the command as the readiness gate before creating a tag. On success, report
its candidate SHA and CI run URL. A readiness-only request ends with the result;
it does not authorize a tag, draft, or publication. On failure, report the
blocker and resolve it before tagging. Do not independently repeat its checks,
inspect its implementation, or reproduce CI locally as part of a routine release.
If the candidate changes, run the gate with the newly selected SHA. Do not run
assessments or alter tracked BOE to make a release pass.

Briefly check open Dependabot alerts and investigate any relevant findings.
Discuss their release impact with the maintainer in the session; this does not
require a recorded decision or introduce another readiness gate. If alerts cannot
be read, say so rather than reporting a clean security backlog.

Use the verified CI run's `static-site` and `skill-catalog.zip` artifacts for any
useful package previews. Follow the shipped guides when trying them. Keep these
checks proportional to the request; do not invent an acceptance process.

## Prepare the draft

For a draft request, use the successful `check-ready` result. Explain that creating
the draft pushes a public version tag and starts the workflow, which checks the
repository, builds the site, packages all four artifacts, and creates an unpublished
draft. Obtain authorization for the tag push unless already covered by the request.
Follow the repository's PR and branch protection rules.

Tag the exact SHA returned by `check-ready` and push only that tag:

```sh
git tag v<version> <candidate-sha>
git push origin refs/tags/v<version>
```

Wait for the tag's `release.yml` run to complete. The workflow is the sole owner
of draft creation and asset uploads. Do not run `gh release create` or repackage
CI previews locally to create a competing draft. If a tag or draft already exists,
inspect its workflow state and continue at the appropriate stage rather than
calling `check-ready` again. Do not move the tag or replace assets to bypass a failure.

## Publish the existing draft

From the clean candidate checkout, run the draft gate with the same version and SHA:

```sh
uv run --group release python -m sklc_maintainer.release check-draft \
  --version <version> --expected-commit <expected-commit-sha>
```

This checks the existing tag, committed notes, draft status, four complete assets
with GitHub digests, and the successful release workflow for that tag and commit.
Trust its result rather than repeating its checks manually. A failed gate blocks
publication; describe the failure and resolve it before proceeding.

Present the draft URL and result. A draft-only request ends here. When the
maintainer authorizes publication, publish that existing draft:

```sh
gh release edit v<version> --repo Code-dot-mil/SkLC --draft=false
```

Its tag already exists, so publishing does not create a new tag push or start a
second preparation workflow. A request to publish a new release can authorize
both stages, but always wait for preparation and run `check-draft` first.

After publication, inspect the release: confirm its commit, version, notes,
prerelease status, and four assets. Download the needed product,
compare its SHA-256 with GitHub's digest once, then unzip or install it and follow its guide.
Report publication and any deployment results. On failure, describe the blocker
and agree on recovery before moving tags or replacing a published release.

Validate changes to the release script through actual release use. Do not add
automated tests for it or create throwaway releases as tests.
