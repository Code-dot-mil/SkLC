# SkLC

SkLC helps teams install, assess, and share **agent skills**: reusable instructions that guide a coding agent through a task, such as reviewing Python code or writing unit tests.

A skill is a folder containing a `SKILL.md` file with its name, description, and instructions, plus any supporting files. Developers install that folder in their workspace so their agent can discover and use it. Teams can assess a skill for potential problems and publish it alongside its review evidence in a **Skill Exchange**, a website for browsing and downloading skills.

You can install skills, run assessments, or host an exchange independently. Start with the task you want to accomplish.

## Choose a starting point

| Your goal | What to use | Guide |
| --- | --- | --- |
| Install the supplied developer skills | **Skill catalog** — four complete skill packages | [Install skills in your workspace](products/skill-catalog/README.md) |
| Assess a skill you wrote or received | **Assessment kit** — a standalone Python command-line tool | [Install the kit and assess a local skill](products/assessment-kit/README.md) |
| Understand an existing assessment | **Assessment kit** plus an existing report pair | [Install the kit](products/assessment-kit/README.md#installation), then [summarize the reports](products/assessment-kit/README.md#summarize) |
| Put the supplied example exchange online | **Prebuilt deployment kit** — a ready-to-host website | [Install the site](products/deployment-kit/prebuilt/docs/install.md), then deploy to [GitLab Pages](products/deployment-kit/prebuilt/docs/deploy-gitlab-pages.md) or [another static host](products/deployment-kit/prebuilt/docs/deploy-static-hosting.md) |
| Publish an exchange containing your team's skills | **Operator deployment kit** — assessment tooling, website source, and a GitLab pipeline | [Set up and maintain your exchange](products/deployment-kit/operator/docs/README.md) |

Download the package for your chosen path from [GitHub Releases](https://github.com/Code-dot-mil/SkLC/releases). Follow its installation guide to compare the download's SHA-256 checksum with the value displayed on the release page; matching checksums verify download integrity. The guides also cover required tools, package contents, and how to verify a successful installation or deployment.

## Use the developer skills

The catalog contains four skills:

- **Secure Python code review:** review Python changes for security weaknesses.
- **Unit test generation:** create focused tests for a change or bug fix.
- **Inline documentation:** explain code through comments, docstrings, and related notes.
- **Change descriptions:** help reviewers understand the purpose, impact, and verification of a change.

Use a coding agent that supports workspace skills in `.agents/skills/`. Install the complete skill folders there, start a fresh agent session, and confirm that the skills appear in its available-skills list. Then ask it to use a skill for a task, for example:

> Use the python-secure-code-review skill to review the Python changes in this branch.

The [catalog installation guide](products/skill-catalog/README.md) explains the archive layout and installation steps. Using the catalog requires neither a hosted exchange nor assessment tooling.

## Understand what assessment tells you

The assessment kit helps an author investigate potential problems before using or sharing a skill. It runs the external **SkillSpector** scanner and, by default, asks a configured model to review the findings in context. This second review is called **adjudication**. Skill contents are sent to the configured model provider.

The kit produces a scanner report and an adjudication report. Its `summarize` command turns that pair into a readable account of confirmed findings to fix, unresolved findings to investigate, false positives, and review limitations. After revising a skill, assess it again to check the new content. See the [assessment guide](products/assessment-kit/README.md) for prerequisites, commands, and result interpretation.

An assessment is evidence for a human decision, not a safety certificate. Adjudication examines `SKILL.md` and scanner evidence; supporting files are not independently reviewed. A successful command can still report problems or incomplete coverage. Read the [review scope](products/assessment-kit/README.md#review-scope) before relying on a judgment.

To read existing results for the supplied skills, download `skill-catalog-assessments-<version>.zip` and follow [Summarize](products/assessment-kit/README.md#summarize). Once the assessment kit is installed, reading these reports needs no scanner or model-provider setup.

## Share skills through an exchange

An exchange lets visitors browse skill descriptions, read instructions and assessment results, and download skill packages and reports. It is a static website: assessment and site building happen before publication, and visitors do not trigger model requests.

Choose **Prebuilt** to host the supplied four-skill catalog without building the site. Choose **Operator** to maintain your own catalog, select any supplied skills you want to include, and run the assessment, build, and publication pipeline. Operator setup requires GitLab runners, an assessment container image, and access to a configured model provider; the [Operator guide](products/deployment-kit/operator/docs/README.md) walks through those requirements and ongoing updates.

Completed negative assessments can remain visible on a published exchange. Publication does not imply that every finding has been resolved; [governance](GOVERNANCE.md) describes human review and approval responsibilities.

## Explore the project or contribute

- [Architecture](docs/architecture.md) explains how the products fit together and how skills and reports become a website.
- [Contributing](CONTRIBUTING.md) covers source development, tool installation, local checks, and generated files. Start here to change SkLC itself.
- [CI and releases](CI.md) explains validation, development-preview downloads, and release preparation.
- [Roadmap](docs/roadmap.md) records planned milestones and future direction.
