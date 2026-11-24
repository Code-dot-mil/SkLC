# Before and after for SkLC PR #132

These 31 comparisons show the documentation reviewed in [PR #132](https://github.com/Code-dot-mil/SkLC/pull/132) across 11 files. Comparisons 1–29 show the [PR base](https://github.com/Code-dot-mil/SkLC/commit/326531668a43e167ad3382ea73d281e71a389bd6) and the [first reviewed revision](https://github.com/Code-dot-mil/SkLC/commit/7c63f7f1924c05a1909a2e415bd8f38c407a35b4). [Comparisons 30 and 31](#follow-up-corrections) show the two subsequent wording fixes. The images use committed Markdown and locally rendered diagrams. Comparison 5 records the original row 4 download paragraph for reference.

## Project README

[Before](https://github.com/Code-dot-mil/SkLC/blob/326531668a43e167ad3382ea73d281e71a389bd6/README.md) · [After](https://github.com/Code-dot-mil/SkLC/blob/7c63f7f1924c05a1909a2e415bd8f38c407a35b4/README.md)

**1. Project introduction.** The opening spells out Skill Lifecycle, describes its tools, and introduces the Skill Exchange.

![Project introduction before and after](01-project-introduction.png)

**2. Exchange diagram.** The original diagram showed the five lifecycle stages. Its replacement shows an operator adding existing skills, assessing them, reviewing the results, and sharing them with their evidence.

![Exchange diagram before and after](02-lifecycle-diagram-and-exchange-workflow.png)

**3. Lifecycle guidance.** The README describes where the tools support validation and release. It points readers to AI4SDLC for guidance on using agents and reviewing their work.

![Lifecycle guidance before and after](03-lifecycle-guidance-and-ai4sdlc.png)

**4. Choosing a download.** The starting-point table drops the fixed skill count. Readers can follow the Architecture link for the relationship between downloads.

![Choosing a download before and after](04-starting-points-and-release-downloads.png)

**5. Workbook row 4.** The release-download paragraph is identical in both revisions. The response on this row concerned the skill list, which is addressed in the next comparison.

![Workbook row 4 before and after](05-row-4-release-paragraph.png)

**6. Using the skill bundle.** The overview directs readers to the bundle guide for the current list and installation steps.

![Using the skill bundle before and after](06-using-the-skill-bundle.png)

**7. Using the assessment kit.** The new wording identifies what goes to the scanner and what goes to adjudication. It describes dismissed alerts as findings judged to be false positives.

![Using the assessment kit before and after](07-using-the-assessment-kit.png)

**8. Sharing and contributing.** The exchange section points readers to Governance for approval responsibilities. The contribution link describes the work its guide covers.

![Sharing and contributing before and after](08-sharing-skills-and-contributing.png)

## Reader profiles

[Before](https://github.com/Code-dot-mil/SkLC/blob/326531668a43e167ad3382ea73d281e71a389bd6/docs/PERSONAS.md) · [After](https://github.com/Code-dot-mil/SkLC/blob/7c63f7f1924c05a1909a2e415bd8f38c407a35b4/docs/PERSONAS.md)

**9. Beginner reading path.** The link label uses the beginner guide’s new title.

![Beginner reading path before and after](09-beginner-guide-reading-path.png)

## Beginner guide

[Before](https://github.com/Code-dot-mil/SkLC/blob/326531668a43e167ad3382ea73d281e71a389bd6/docs/using-skills.md) · [After](https://github.com/Code-dot-mil/SkLC/blob/7c63f7f1924c05a1909a2e415bd8f38c407a35b4/docs/using-skills.md)

**10. Agent and skill definitions.** The guide introduces the agent first and illustrates a skill with a unit-test example.

![Agent and skill definitions before and after](10-agent-and-skill-definitions.png)

**11. Prerequisites and task fit.** The prerequisites come before browsing. Task fit remains the first checklist question, followed by agent compatibility, other requirements, and information handling.

![Prerequisites and task fit before and after](11-what-you-need-to-use-a-skill.png)

**12. Finding skills.** Readers can browse before installing software. The guide explains where an organization’s exchange fits.

![Finding skills before and after](12-where-to-find-skills.png)

**13. Reading an assessment.** Readers can open Assessment Evidence or follow the guide for downloaded reports. The passage discussed in deferred row 32 retains its original wording.

![Reading an assessment before and after](13-reading-an-assessment.png)

**14. Installing and trying a skill.** The exchange download step leads to installation. The guide includes the agreed unit-test prompt and explains how a team can version a complete skill folder with its project.

![Installing and trying a skill before and after](14-installing-trying-and-maintaining-a-skill.png)

## Skill bundle

[Before](https://github.com/Code-dot-mil/SkLC/blob/326531668a43e167ad3382ea73d281e71a389bd6/products/skill-bundle/README.md) · [After](https://github.com/Code-dot-mil/SkLC/blob/7c63f7f1924c05a1909a2e415bd8f38c407a35b4/products/skill-bundle/README.md)

**15. Agent prerequisites.** Readers check their agent’s documented installation location. The guide retains the command-line prerequisite.

![Agent prerequisites before and after](15-agent-prerequisites.png)

**16. Verifying and extracting the skill bundle.** The guide gives labeled checksum and extraction commands for the reader’s operating system.

![Verifying and extracting the skill bundle before and after](16-verifying-and-extracting-the-skill-bundle.png)

**17. Installing skills and finding their reports.** The project path is an example of a supported install location. The fresh-session instruction is retained, and the reports walkthrough becomes a link to the results guide.

![Installing skills and finding their reports before and after](17-installing-skills-and-finding-the-reports.png)

**18. CI artifact walkthrough.** The release bundle guide drops the development-preview section.

![CI artifact walkthrough before and after](18-removed-ci-artifact-walkthrough.png)

## Assessment kit

[Before](https://github.com/Code-dot-mil/SkLC/blob/326531668a43e167ad3382ea73d281e71a389bd6/products/assessment-kit/README.md) · [After](https://github.com/Code-dot-mil/SkLC/blob/7c63f7f1924c05a1909a2e415bd8f38c407a35b4/products/assessment-kit/README.md)

**19. Assessment kit audience.** The introduction removes the assumption that a colleague is available to help with setup.

![Assessment kit audience before and after](19-audience-and-setup-help.png)

**20. Assessment scope.** The two original scope paragraphs are reordered so the reader encounters the scan before adjudication.

![Assessment scope before and after](20-assessment-scope-and-human-review.png)

**21. Scanner prerequisites.** The guide states when SkillSpector is needed and removes the aside about wheel installation.

![Scanner prerequisites before and after](21-scanner-prerequisites.png)

**22. Verifying the wheel.** Linux, macOS, and Windows each have a labeled checksum example using the wheel filename.

![Verifying the wheel before and after](22-wheel-verification-on-each-platform.png)

**23. Diagnostic log.** The standalone guide describes the log as diagnostic output and removes the version-control aside.

![Diagnostic log before and after](23-diagnostic-log-guidance.png)

## Assessment reports

[Before](https://github.com/Code-dot-mil/SkLC/blob/326531668a43e167ad3382ea73d281e71a389bd6/products/skill-bundle-assessments/README.md) · [After](https://github.com/Code-dot-mil/SkLC/blob/7c63f7f1924c05a1909a2e415bd8f38c407a35b4/products/skill-bundle-assessments/README.md)

**24. Verifying and extracting the reports ZIP.** Readers get checksum and extraction steps for the reports archive on their operating system.

![Verifying and extracting the reports ZIP before and after](24-verifying-and-extracting-the-reports-zip.png)

## Prebuilt installation

[Before](https://github.com/Code-dot-mil/SkLC/blob/326531668a43e167ad3382ea73d281e71a389bd6/products/deployment-kit/prebuilt/docs/install.md) · [After](https://github.com/Code-dot-mil/SkLC/blob/7c63f7f1924c05a1909a2e415bd8f38c407a35b4/products/deployment-kit/prebuilt/docs/install.md)

**25. Installing the Prebuilt ZIP.** The guide quotes the versioned filenames and provides both shell and PowerShell extraction steps.

![Installing the Prebuilt ZIP before and after](25-verifying-and-extracting-the-prebuilt-zip.png)

## Operator setup

[Before](https://github.com/Code-dot-mil/SkLC/blob/326531668a43e167ad3382ea73d281e71a389bd6/products/deployment-kit/operator/docs/README.md) · [After](https://github.com/Code-dot-mil/SkLC/blob/7c63f7f1924c05a1909a2e415bd8f38c407a35b4/products/deployment-kit/operator/docs/README.md)

**26. Operator introduction.** The guide moves from the purpose of the Operator kit directly to what the reader will set up.

![Operator introduction before and after](26-operator-guide-introduction.png)

**27. Operator download.** The guide reuses the download-verification steps and identifies the Operator filename and extraction directory to use.

![Operator download before and after](27-reusing-the-download-instructions.png)

## Governance

[Before](https://github.com/Code-dot-mil/SkLC/blob/326531668a43e167ad3382ea73d281e71a389bd6/GOVERNANCE.md) · [After](https://github.com/Code-dot-mil/SkLC/blob/7c63f7f1924c05a1909a2e415bd8f38c407a35b4/GOVERNANCE.md)

**28. Official bundle approval.** The governance page explains human approval of upstream changes and the current SAFE assessment requirement for official bundle releases.

![Official bundle approval before and after](28-official-release-approval-and-operator-publication.png)

## Architecture

[Before](https://github.com/Code-dot-mil/SkLC/blob/326531668a43e167ad3382ea73d281e71a389bd6/docs/architecture.md) · [After](https://github.com/Code-dot-mil/SkLC/blob/7c63f7f1924c05a1909a2e415bd8f38c407a35b4/docs/architecture.md)

**29. Architecture introduction.** The architecture guide directs readers choosing a download back to the README and keeps its own introduction focused on product relationships.

![Architecture introduction before and after](29-architecture-guide-introduction.png)

## Follow-up corrections

**30. Installing the CI preview.** The preview download entry now gives the extraction folder and the point at which to resume the packaged installation guide. [Before](https://github.com/Code-dot-mil/SkLC/blob/89ee7b7eb6b6bf3bb44de339045e44b29886bdcd/CI.md#L86) · [After](https://github.com/Code-dot-mil/SkLC/blob/aeccb556539b5b3c92d4d25179afae65b9ed85d1/CI.md#L86)

![Skill bundle CI preview instructions before and after](30-ci-preview-installation.png)

**31. Skill installation location.** The architecture table directs readers to their agent’s documented location, and the diagram labels the result “Installed skills.” [Before](https://github.com/Code-dot-mil/SkLC/blob/89ee7b7eb6b6bf3bb44de339045e44b29886bdcd/docs/architecture.md#L7) · [After](https://github.com/Code-dot-mil/SkLC/blob/aeccb556539b5b3c92d4d25179afae65b9ed85d1/docs/architecture.md#L7)

![Architecture table and product diagram before and after](31-architecture-skill-location.png)
