# SkLC delivery roadmap

SkLC's delivery goal is independently usable products: teams can install skills, assess skills, or host an exchange without adopting the maintainer repository and its release workflows. The [README](../README.md) is the starting point for current use; [architecture](architecture.md) explains the product relationships.

This roadmap separates capabilities present in source from evidence that a released download works for its intended consumer. Implementation status alone does not establish a published release, a successful customer deployment, or completion of a milestone.

## What is implemented

| Capability in this repository | Current scope | Delivery evidence still matters |
| --- | --- | --- |
| Initial skill catalog | Four developer skills and a standalone ZIP assembler. | Download, verify, install in a clean workspace, and confirm agent discovery. |
| Assessment kit | Wheel packaging; `validate`, `hash`, `assess`, and `summarize`; one selected skill per invocation. | Install the released wheel outside the checkout and assess a local skill with the supported scanner/provider. |
| Catalog evidence and automation | Separate assessment download; same-repository PR feedback and main-branch assessment/report maintenance. | Matching source/report downloads and review feedback from the relevant workflow run. This automation is implemented, rather than a deferred feature. |
| Prebuilt deployment | Static-site assembly, deployment guides, and deploy-only GitLab Pages CI. | Deploy the downloaded kit unchanged in a clean GitLab project and verify site/downloads. |
| Operator deployment and updates | Bundled assessment wheel, site/runtime source, reference GitLab pipeline, live catalog separation, and whole-component update instructions. | Install, assess, build, deploy, retain evidence, and update outside the maintainer checkout. |
| Standalone assessment GitLab profile | Reference job source under `products/assessment-kit/ci/gitlab/`. | Supported consumer packaging and a clean-project run remain distinct from the profile's presence in source. |

The release workflow assembles four ZIPs plus the assessment wheel under one release version. These are the catalog, its companion assessments, Prebuilt and Operator deployment modes, and the assessment CLI. A reference CI profile is not a separate product; its source is not an additional standalone release asset. See [CI and releases](../CI.md#releases) for the actual asset list and preparation procedure.

Skill lifecycle guidance is a fourth product track, published separately from the Code-dot-mil AI4SDLC GitHub after its minimum useful shape is agreed. It is not a prerequisite for the products above.

## Delivery priorities

The original delivery sequence remains: prove Prebuilt delivery first, then independent catalog and assessment use, customer CI, Operator deployment, and updates. Lifecycle guidance progresses in parallel; maintainer assessment is already implemented supporting automation. The numbered sections below group acceptance criteria by outcome, rather than labeling every section as unfinished work. The earlier Q3 2026 target was to prove GitHub-to-GitLab Prebuilt delivery and establish release scope for the other products; the date is a target, not evidence of completion.

For each milestone, retain acceptance evidence from the released artifact and its intended environment. Keep unresolved delivery checks visible instead of treating a source directory, passing unit test, or draft archive as customer acceptance. The criteria below define what to demonstrate; this document does not claim every criterion has been completed.

**Acceptance status is unrecorded here:** this roadmap does not link completed release or customer-verification records for the milestones below. That does not establish that the work is undone. The next delivery task is to locate and link existing evidence against these criteria, then address the earliest unmet outcome in the delivery sequence. Reuse valid evidence rather than repeating work solely because its record is missing from this page.

### 1. Prebuilt exchange delivery

**Outcome:** A customer downloads a finished exchange and deploys it unchanged to GitLab Pages.

The ZIP contains static files/downloads, deployment-only CI, and installation/deployment documentation. Installation requires neither assessment tooling nor a website build. The milestone does not include Operator customization, a separate catalog release, or generic static-host validation.

**Acceptance:** Obtain the release through GitHub, compare its SHA-256 with the asset digest, unpack once, and deploy in a clean GitLab project using only the shipped guide and CI. Verify the website and skill downloads.

### 2. Independent developer catalog

**Outcome:** A developer obtains four complete skill packages and installs them in a workspace.

The catalog includes secure Python code review, unit test generation, inline documentation, and change descriptions, with committed supporting files and an installation README. Catalog packaging is independent of assessment and site generation. Matching assessment pairs are now a separate companion download; operators copy selected upstream skills and evidence explicitly.

**Acceptance:** The ZIP contains exactly the selected complete packages and README, its digest matches, unrelated/untracked source is absent, and a fresh agent session discovers the skills copied into `.agents/skills/` in a clean workspace.

### 3. Independent assessment kit

**Outcome:** A developer installs the wheel and assesses a local skill without the catalog, site, GitLab project, or deployment kit.

The foundation has four commands, one explicitly selected skill per assessment, a public package hash, supported SkillSpector CLI/report compatibility, and current report replacement with optional unchanged-content reuse. It produces original scanner findings, adjudication, and action summaries. It does not make publication decisions, assemble catalogs, deploy sites, or impose a fixed consumer repository layout.

**Acceptance:** Download and verify the wheel, install it in an isolated environment outside the checkout, configure the scanner/provider, assess a local package, and render a summary. Reports identify the assessed package and explain scope, limitations, and actions. The wheel version corresponds to the release version under Python normalization.

### 4. Customer assessment CI

**Outcome:** A team can use a supported GitLab assessment profile without designing the jobs itself.

The profile needs explicit skill/output locations, an image with the scanner, provider settings/credentials, and artifact retention. Its scope is assessment and summaries, with manual retention of durable evidence. Catalog assembly, deployment, MR comments, and bot-driven report commits are outside this milestone.

**Acceptance:** Package and document the consumer entry point, configure it in a clean GitLab project, run assessment once, retain native reports, adjudication, diagnostics and the action summary, and confirm that the job makes no source-control changes. Source availability alone does not establish this delivery path.

### 5. Maintainer catalog assessment

**Outcome:** Maintainers receive actionable feedback on proposed skill changes and retain matching evidence after merge.

The implemented GitHub jobs use the public assessment kit from the checkout. Same-repository PRs assess selected changes for review; main maintains current report pairs. Provider access belongs on an approved self-hosted runner; other checks stay on hosted runners. Fork previews do not receive provider credentials. Assessment feedback does not change catalog approval policy.

**Acceptance:** Inspect the PR summary and retained reports for the assessed revision, then verify that successful main assessment stores only current report pairs and removes obsolete pairs appropriately. Review the resulting source/evidence association in downloads.

### 6. Operator installation and publication

**Outcome:** An operator installs a released kit in a clean GitLab project and publishes an exchange for its chosen catalog.

The kit assembles compatible catalog/evidence artifacts, an exact assessment wheel, site/runtime source, and customer CI. Operators can include all, some, or none of the supplied skills alongside their own. The pipeline assesses or reuses current reports, summarizes results, builds the site, and produces a Pages artifact. Evidence retention uses job artifacts and documented manual commits; the pipeline makes no commits or pushes by default.

**Acceptance:** Use the shipped guide outside the maintainer checkout. Configure each required runner, credential, image, and provider setting; validate installed catalog inputs; assess each changed skill once; verify summaries, retained diagnostics, the website, skill ZIPs and report downloads. Document supported environment constraints and any deferred needs.

### 7. Operator-managed updates

**Outcome:** Operators update upstream components while preserving live catalog content and matching evidence.

Update archives exclude live `skills/` and `evidence/`. Included upstream content is staged under `upstream/` for explicit selection. Updates replace upstream-owned components completely so removed files disappear. A customized UI, CI, assessment toolchain, or runtime becomes a whole component owned by the operator and excluded from replacement/extraction.

**Acceptance:** Exercise installation with all, some, and none of the supplied skills alongside customer content. Then exercise a full update and an update preserving a customized component. Verify that live skill/evidence bytes survive, removed upstream files disappear, excluded components remain unchanged, and the included source and exact wheel install and rebuild outside the checkout.

## Parallel track: lifecycle guidance

The first guidance bundle should help readers identify a skill's stage and choose a next action using **Define, Build, Validate, Release, and Operate**. Roles—user, author, reviewer, operator—remain secondary to those stages. Approval authority is recorded at Release without creating another standing lifecycle role.

The minimum useful guidance shape, smallest useful skill record, and approval-recording approach still need agreement. Record the uncertainty, proposed direction, and open questions in a dated note under `research/` in the [skill-lifecycle research repository](https://gitlab.mitre.org/dod-ai4sdlc/skill-lifecycle), following that repository's conventions. Plan the first guidance release after those decisions are accepted; the research repository is separate from the intended guidance publication origin.

This track does not gate the catalog, assessment kit, or deployment kit. It does not require a repository rename, workflow engine, generated guidance system, heavy governance model, or mandatory evaluation program.

## Deferred capabilities and limits

The assessment CLI currently selects one skill. Multi-skill invocation, recursive discovery, reusable configuration files, machine-readable advice manifests, and additional assessors remain future capabilities to justify through consumer need.

Operator support does not promise offline/air-gapped operation, historical skill serving, obsolete scanner-format compatibility, incremental merging of customized components, a separate updater service, or compatibility with arbitrary replacement sites/deployment systems. Additional retention or update automation needs demonstrated customer demand.

## Release and ownership rules

The maintainer GitHub repository remains the source of truth and release origin specified in [requirements](decisions.md); customers receive artifacts rather than mirroring maintainer source or importing upstream workflows. Lifecycle guidance has its separate publication origin.

Every artifact in an SkLC release uses that release's version, with Python normalization for the wheel. Components do not have independent version streams. Products can stand alone while deployment assembly bundles the components its consumer workflow needs. The normative [product-boundary contract](product-boundaries.md) defines source ownership, permitted dependencies, and independence checks.
