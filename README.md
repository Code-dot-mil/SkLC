# SkLC

Skill Lifecycle (SkLC) helps teams use, assess, and share **agent skills**.

An **AI agent** is an AI application that can carry out tasks using instructions and tools. A **skill** gives an agent reusable instructions for a particular task. For example, a team could write a skill to help an agent check a document against a checklist, so people do not have to explain the same process each time.

SkLC provides tools for assessing skills for potential problems and sharing them alongside review evidence. Its **Skill Exchange** is a website where people can browse skills, read their instructions and assessment results, and download them for use with a compatible agent.

**New to AI agents or skills?** Start with [Using a skill](docs/using-skills.md) to understand what you need, how to choose a skill, and what to check before relying on its results. You can read about skills without installing software.

## The skill lifecycle

A skill needs more than useful instructions. Its authors need to understand who will use it, check that it behaves as intended, decide when it is ready to share, and revisit those decisions as the skill, model, or environment changes.

The Skill Lifecycle organizes that work into five stages:

![Five stages: Define, Build, Validate, Release, and Operate. A revision loop connects the stages so feedback can lead to further definition, changes, and testing.](docs/assets/skill-lifecycle-overview.svg)

| Stage | What it accomplishes |
| --- | --- |
| **Define** | Establish the problem, intended users, expected behavior, and who is responsible for the skill. |
| **Build** | Write the instructions and add the examples, scripts, or other supporting material the task needs. |
| **Validate** | Check when the skill activates, the quality of its results, and potential safety or security problems. Gather evidence for the release decision. |
| **Release** | Decide whether a version is ready for its intended users and make it available with the relevant review evidence. |
| **Operate** | Collect feedback, investigate failures, and reassess the skill as its dependencies, models, or operating conditions change. Update or retire it when needed. |

These stages form a cycle. Feedback during use—or a problem found during validation—can send a skill back for further definition, changes, and testing.

The tools in this repository support parts of that lifecycle. The assessment kit helps gather validation evidence, while the catalog and deployment kits help distribute skills and assessment reports. Teams remain responsible for task-specific testing, release decisions, and ongoing review.

## Choose a starting point

You can install skills, run assessments, or host an exchange independently. Start with the task you want to accomplish.

| Your goal | What to use | Guide |
| --- | --- | --- |
| Install the supplied skills | **Skill catalog** — four complete skill packages | [Install skills in your workspace](products/skill-catalog/README.md) |
| Assess a skill you wrote or received | **Assessment kit** — a standalone Python command-line tool | [Install the kit and assess a local skill](products/assessment-kit/README.md) |
| Understand an existing assessment | **Assessment kit** plus an existing report pair | [Install the kit](products/assessment-kit/README.md#installation), then [summarize the reports](products/assessment-kit/README.md#summarize) |
| Put the supplied example exchange online | **Prebuilt deployment kit** — a ready-to-host website | [Install the site](products/deployment-kit/prebuilt/docs/install.md), then deploy to [GitLab Pages](products/deployment-kit/prebuilt/docs/deploy-gitlab-pages.md) or [another static host](products/deployment-kit/prebuilt/docs/deploy-static-hosting.md) |
| Publish an exchange containing your team's skills | **Operator deployment kit** — assessment tooling, website source, and a GitLab pipeline | [Set up and maintain your exchange](products/deployment-kit/operator/docs/README.md) |

Download the package for your chosen path from [GitHub Releases](https://github.com/Code-dot-mil/SkLC/releases). Follow its installation guide to compare the download's SHA-256 checksum with the value displayed on the release page; matching checksums verify download integrity. The guides also cover required tools, package contents, and how to verify a successful installation or deployment.

## Use the supplied skills

The supplied catalog contains four skills for software tasks:

- **Secure Python code review:** review Python changes for security weaknesses.
- **Unit test generation:** create focused tests for a change or bug fix.
- **Inline documentation:** explain code through comments, docstrings, and related notes.
- **Change descriptions:** help reviewers understand the purpose, impact, and verification of a change.

Use an AI agent that supports workspace skills in `.agents/skills/`. Install the complete skill folders there, start a fresh agent session, and confirm that the skills appear in its available-skills list. Then ask it to use a skill for a task, for example:

> Use the python-secure-code-review skill to review the Python changes in this branch.

The [catalog installation guide](products/skill-catalog/README.md) explains the archive layout and installation steps. Using the catalog requires neither a hosted exchange nor assessment tooling.

## Understand what assessment tells you

The assessment kit helps an author investigate potential problems before using or sharing a skill. It runs the external **SkillSpector** scanner and, by default, asks a configured model to review the findings in context. This second review is called **adjudication**. Skill contents are sent to the configured model provider.

The kit produces a scanner report and an adjudication report. Its `summarize` command turns that pair into a readable account of confirmed problems to address, findings that still need investigation, alerts dismissed after contextual review (false positives), and review limitations. After revising a skill, assess it again to check the new content. See the [assessment guide](products/assessment-kit/README.md) for prerequisites, commands, and result interpretation.

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
- [Product decisions](docs/decisions.md) records accepted requirements and the parallel lifecycle-guidance direction.
