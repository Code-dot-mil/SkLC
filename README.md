# SkLC: install, assess, and share agent skills

SkLC helps teams use and share agent skills: reusable instruction packages that guide a coding agent through a task. Each skill is a directory with a `SKILL.md` file containing its name, description, and instructions, plus any supporting files.

For example, a developer can install the supplied Python code review skill in a workspace. A skill author can assess their own instructions and investigate potential problems. A team can publish skills and their assessment results through a static website called a Skill Exchange.

You can use these capabilities independently. Choose the path that matches your task below. For an overview of how the products fit together, read the [architecture guide](docs/architecture.md).

## Choose your starting point

| I want to… | Use | Start here |
| --- | --- | --- |
| Install developer skills in my coding agent's workspace | Skill catalog: four complete skill packages | [Install the catalog](products/skill-catalog/README.md) |
| Assess a local skill and understand which findings need attention | Assessment kit: a standalone Python CLI | [Install and use the assessment kit](products/assessment-kit/README.md) |
| Host the supplied example exchange without building a website | Deployment kit, Prebuilt mode: a finished static site | [Install the prebuilt site](products/deployment-kit/prebuilt/docs/install.md), then deploy to [GitLab Pages](products/deployment-kit/prebuilt/docs/deploy-gitlab-pages.md) or [another static host](products/deployment-kit/prebuilt/docs/deploy-static-hosting.md) |
| Assess my own catalog and build an exchange for it | Deployment kit, Operator mode: assessment tooling, site source, and a GitLab pipeline | [Set up an Operator instance](products/deployment-kit/operator/docs/README.md) |

The catalog includes secure Python code review, unit test generation, inline documentation, and change descriptions. You can install these skills without hosting an exchange or running an assessment.

Download the product you need from [GitHub Releases](https://github.com/Code-dot-mil/SkLC/releases). Before using it, calculate its SHA-256 and compare it with the digest GitHub displays for that asset. Each installation guide explains its requirements and package layout. Downloads from [CI runs](https://github.com/Code-dot-mil/SkLC/actions/workflows/ci.yml) are development previews; see [CI package details](CI.md#github-validation).

## Understand assessment results

The assessment kit uses the external SkillSpector scanner to identify potential problems in a skill. By default, it also asks a configured model to review the findings in context. That review is called adjudication: it distinguishes confirmed findings, false positives, and findings that still need investigation. Skill contents are sent to the configured provider.

Use `skill-assessment summarize` to turn the scanner report and adjudication into a Markdown summary of required remediation, unresolved findings, false positives, and limitations. After installing the kit, summarize an existing report pair with:

```sh
uv run --no-project skill-assessment summarize --assessment-dir ./reports
```

Run this from the working directory containing the virtual environment created during installation. Here, `./reports` is a directory containing both `skillspector.json` and `adjudication.json`. The separate `skill-catalog-assessments-<version>.zip` release download contains one such pair per supplied catalog skill. Point the command at the selected skill's directory. Summarizing existing reports needs no scanner or provider configuration.

Assessment helps inform a human decision; command success does not establish that a skill is safe. Adjudication examines `SKILL.md` and scanner evidence, while supporting files are not independently reviewed. Read the [assessment guide's scope and limitations](products/assessment-kit/README.md#review-scope) before relying on a result. Human review and approval responsibilities are described in [governance](GOVERNANCE.md).

## Host and maintain an exchange

Prebuilt mode serves the supplied four-skill catalog as a finished website. You need a static host; deploying the package requires no Python, Node.js, or assessment toolchain.

Operator mode is for a catalog you maintain. You select any included upstream skills you want, add your own, and run **Assess → Generate → Build → Pages**. Its [installation guide](products/deployment-kit/operator/docs/README.md) covers runner access, the assessment image, provider configuration, evidence retention, and updates.

Both modes produce a static website where visitors can browse skill instructions, download packages, and inspect assessment evidence. Visitors do not trigger scans or model requests. An Operator pipeline requires completed matching assessments to build the site, but negative judgments and coverage limitations remain visible advisory results rather than automatically blocking publication.

## Contribute to SkLC

For source development, follow [Contributing](CONTRIBUTING.md). Start with the [development and lint prerequisites](docs/linting.md), then run the common checks from the repository root:

```sh
just ci-local
```

To generate catalog data from existing assessments and build the website:

```sh
just build
```

The build writes derived catalog data to `.exchange/local-generated/` and site output to `products/deployment-kit/operator/site/dist/`. It reads current assessment reports without changing them or running a scanner.

For further reading, use the [architecture](docs/architecture.md) for component relationships, [product boundaries](docs/product-boundaries.md) for source ownership and dependencies, and [CI](CI.md) for validation, preview downloads, and releases. The [roadmap](docs/roadmap.md) records intended milestones; use the linked product guides for current usage instructions. [Reader profiles](docs/PERSONAS.md) describe the audiences this documentation serves.
