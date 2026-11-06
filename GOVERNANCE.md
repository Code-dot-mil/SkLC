# How skill changes are reviewed

SkLC uses human review to decide which skill changes to accept. Assessment results help reviewers investigate problems; they do not approve a skill or replace that decision.

This document describes review in the upstream SkLC repository. Teams running their own Operator exchange also need to establish who can approve publication in their environment.

## Who does what?

| Participant | Responsibility |
| --- | --- |
| Contributor | Propose skill or application changes through a pull request and explain their purpose. |
| Human reviewer | Inspect a skill's purpose, metadata, instructions, supporting files, and assessment evidence. At least one human reviewer inspects skill changes before merge. |
| Maintainer | Approve changes after human review and merge accepted contributions. |

Skills declare their name and description in `SKILL.md`; the exchange presents that metadata alongside their full instructions. Review the whole package, including supporting files that adjudication does not independently examine.

## From proposed change to published evidence

1. **Propose the change.** Submit the skill package and explain its intended use. Use [Contributing](CONTRIBUTING.md) for platform changes and local checks; it is not a separate skill-submission procedure.
2. **Review the content and results.** Read the assessment's confirmed findings, unresolved findings, false-positive reasons, scope, and limitations. The [assessment guide](products/assessment-kit/README.md#summarize) explains how to obtain and interpret that summary.
3. **Make the human decision.** A maintainer approves changes after human review. An automated scan completing successfully is not that approval.
4. **Keep evidence tied to the accepted content.** The main assessment workflow maintains current report pairs for bundled skills. Site generation checks that each pair describes the exact skill being published. See [CI](CI.md#main-bundle-assessments) for how upstream automation retains the evidence.

## What the publication checks establish

An assessed site needs matching reports, successful scanner execution, completed adjudication, and a determination associated with every scanner finding. Missing, stale, or mismatched evidence stops site generation. This prevents the site from presenting a report for different skill contents as current evidence.

Those checks establish report eligibility, not approval or absence of risk. Completed negative safety judgments and nonfatal coverage limitations remain advisory and may appear on a published site. The independent skill-bundle download packages skill files without requiring assessment.

The repository does not define a severity-based approval threshold, a formal risk-acceptance record, or an escalation process for disputed findings. These are policy gaps, not permissions granted by a successful build. Reviewers should surface unresolved decisions for the maintainer rather than infer that the pipeline has settled them. Customer operators must define their own publication authority and decision process.

## Preserve the review record

Current reports are `skillspector.json` and `adjudication.json` under `products/skill-bundle-assessments/<skill-name>/`. Git preserves earlier committed results. Keep each pair together and regenerate it through assessment when skill contents change; do not edit report judgments or hashes to make a build pass.

The site index, copied reports, and skill ZIPs are derived output. Generate them rather than committing them. Credentials and environment-specific deployment settings belong outside the repository.

Operator pipelines retain evidence as job artifacts and make no source-control changes. Operators who need durable history must review and commit retained report pairs with their matching catalog revision; see the [Operator guide](products/deployment-kit/operator/docs/README.md#retain-evidence-and-run-again).
