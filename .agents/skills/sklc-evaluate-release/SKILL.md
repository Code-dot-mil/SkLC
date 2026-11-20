---
name: sklc-evaluate-release
description: Evaluate released SkLC products as a consumer, exercise catalog skills and the assessment CLI, and deploy Prebuilt and Operator kits to designated preview repositories.
metadata:
  internal: "true"
---

# Evaluate released products

Evaluate one published release using its downloads outside the upstream checkout. Follow the guides inside those downloads; record documentation failures rather than repairing products from upstream source. This companion to release preparation gathers consumer evidence; it does not create or publish a release.

## Establish the evaluation

Resolve the release repository, tag, release URL, and designated preview repositories for **Prebuilt** and **Operator** from the request or available configuration. Record each target's clone URL, mode, default branch, Pages address, and current revision. Keep organization names, hostnames, and credentials in local configuration outside this skill.

Use existing authorization to deploy to the designated targets. If targets or deployment authority are missing, complete local evaluation and request only what is missing before remote changes. Inspect populated targets and preserve preview-owned content. Use ordinary commits and pushes. If a shipped installation requires an empty repository but the target is populated, agree a safe update approach with its owner before replacement; never force-push or blindly overwrite it.

Create an evaluation directory outside the upstream checkout with separate extraction directories and a fresh Python environment. Record prerequisites and tool versions from the shipped guides. Download these five assets from the same release:

- `skill-catalog-<version>.zip`
- `skill-catalog-assessments-<version>.zip`
- `skill_assessment-<version>-py3-none-any.whl` (Python-normalized version)
- `deployment-kit-prebuilt-<version>.zip`
- `deployment-kit-operator-<version>.zip`

Verify every SHA-256 against the release asset digest before extraction or installation. Record release/tag commit, asset names, and digests. Missing assets, mixed versions, or mismatched hashes block affected checks. Preserve hidden CI files. CI preview downloads are a separate scope: identify them by run and commit rather than presenting them as released products.

## Exercise catalog and assessment downloads

1. Install complete catalog folders into an isolated agent workspace using the catalog README. Confirm discovery in a fresh agent session. Exercise each supplied skill on a representative disposable task matching its description. Retain the task, observable result, and manual corrections; package presence alone does not establish behavior.
2. Install the downloaded wheel in the fresh environment using its README. Invoke installed `skill-assessment --help` outside the upstream checkout. Run public `validate` and `hash` commands on an extracted skill. Verify rejection of invalid frontmatter using a disposable copy, preserving the original.
3. Extract the assessments download separately. Run `summarize` on each shipped pair. Check correspondence with catalog bytes using the installed public hashing/current-evidence interface documented by that version; summarization alone does not establish freshness. Preserve negative judgments and coverage limitations as evidence.
4. Review a disposable skill before sending its contents to an authorized scanner/model provider. Configure SkillSpector and adjudication as documented, then run `assess` and `summarize` with reports outside the skill directory. Inspect exit status, findings, adjudication, scope, and coverage. Static-only diagnostics cannot substitute for the LLM-assisted evidence required by Operator. Record missing provider access as blocked rather than silently changing modes.

Complete this stage with command results and agent-task observations, or an explicit failed/blocked result for each capability.

## Deploy Prebuilt to its preview repository

Follow the extracted Prebuilt installation and Pages guides. Verify `public/`, guides, and hidden `.gitlab-ci.yml` are included. Configure `PAGES_RUNNER_TAG` and documented image overrides for the environment. Deploy the extracted finished site to the confirmed default branch; Prebuilt requires no Python generation, npm build, scanner, or provider.

Record the pushed commit and exact pipeline/job URLs. Wait for deployment to finish, investigate failures, and open the Pages URL reported by the host. Verify the live experience below; a green pipeline alone is insufficient.

## Deploy Operator to its preview repository

Follow the extracted Operator guide, including its bundled assessment wheel and container recipe. Use included components and declared prerequisites without dependencies on sibling products or upstream maintainer tooling.

Select explicit live `skills/` contents; bundled `upstream/` packages are not automatically served. Copy matching evidence when selecting bundled skills. Add a small benign evaluation skill without reports to exercise fresh assessment in customer CI. Record which packages should reuse evidence and which should be scanned.

Build/publish the documented assessment image for the runner architecture when needed, or verify an existing compatible image. Record its digest. Configure `ASSESSMENT_IMAGE`, `ASSESSMENT_RUNNER_TAG`, `BUILD_RUNNER_TAG`, `PAGES_RUNNER_TAG`, and documented provider/model/trust settings. Keep credentials in protected, masked CI variables; ensure the deployment branch can receive them. Runner image-pull access is separate from workstation registry access.

Commit the installed kit and selected catalog, push to the confirmed branch, and follow the exact pipeline through assessment, generation, build, and Pages deployment. Verify fresh paired evidence for the evaluation skill and eligibility of reused evidence. Generation reads matching reports without performing assessments. Retain the specific job's evidence artifact; the pipeline does not commit it. Preserve existing reports before replacement.

Verify the live site below. Change the disposable evaluation skill, rerun CI, and confirm evidence and published content follow the new revision. Exercise a missing/stale-evidence failure in a local disposable kit copy or isolated nonpublishing pipeline: generation must fail rather than substitute evidence. Preserve the working preview and never manufacture reports to pass a gate.

## Verify the deployed consumer experience

For each preview, use its actual published URL, including any project-path prefix:

- Open the catalog and a skill detail page. Check styling, navigation, search/filter behavior exposed by that version, and failed asset requests.
- Read instructions and assessment information. Confirm judgments and partial coverage agree with downloaded reports and remain visible.
- Download a skill ZIP and its report files. Inspect package completeness and compare contents with evaluated release or Operator inputs.
- For Operator, confirm selected live skills and the changed evaluation skill appear, while unselected upstream packages do not.

Record observed outcomes, final URL, deployed commit, and pipeline/job IDs for both modes. Record missing browser/network access as an unverified live check; local builds cannot establish deployment success.

## Report results and clean up evaluation artifacts

Report each asset and both previews with expected behavior, commands/tasks performed, observations, evidence locations, and pass/fail/blocked status. Separate product defects, environment failures, and documentation gaps. Include release provenance, checksums, image digest, deployment revisions, skill-task corrections, and assessment limitations. Redact credentials and credential-bearing diagnostics before sharing.

Stop retries when failure requires changed inputs, permissions, or configuration; report the cause and next action. Retain reports and downloaded evidence in the agreed evaluation location. Remove disposable environments and local build output after preserving evidence. Leave preview deployments available for review unless teardown was requested; state remaining repositories, images, and CI configuration. Claim completion only for checks actually exercised.
