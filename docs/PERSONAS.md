# Documentation readers

The README serves both people exploring AI-assisted work and teams choosing among installing skills, assessing skills, and hosting an exchange. The newcomer profile assumes no technical or AI knowledge. Technical knowledge is specific to the other roles below, rather than a prerequisite for the project introduction. These audience choices are confirmed; the encounter scenarios and detailed reading needs are inferred from supported workflows and can be refined through reader feedback.

## Someone exploring AI-assisted work

**Goal:** Understand whether skills could help with their work and what they need to try one.

**Already knows:** No assumed knowledge of AI, agents, skills, software development, Git, or command-line tools.

**Likely encounter:** Follows a colleague's link, a presentation, or a team initiative to the repository or an exchange. May want to understand the idea before choosing an application or asking for setup help.

**Needs explained:** What an agent and a skill are, how a skill differs from the application that uses it, what an exchange offers, and why instructions and results need review.

**Questions:** What can I do here? Do I need to install anything to read about a skill? Will this skill work with my application and my task? What access or software does it need? Who can help me get started? Does an assessment mean I can trust every result?

**Success:** Explains what a skill does, distinguishes browsing from using it, identifies compatibility and task requirements, and chooses either a suitable next step or a concrete question for their team's support contact.

**Reading path:** [Project introduction](../README.md) → [Using a skill](using-skills.md) → a skill's description and instructions on an exchange, or the [supplied bundle](../products/skill-bundle/README.md) when its software tasks fit their needs. Installation and assessment setup can be handed to a technical colleague.

## A team choosing a starting point

**Goal:** Decide whether to install skills, assess a skill, or host an exchange.

**Already knows:** How to work in a source repository and run documented commands.

**Needs explained:** What an agent skill contains, why assessment is useful, and how the skill bundle, assessment kit, and deployment modes differ.

**Questions:** What problem does SkLC solve? Which download fits my task? What else must I install? Can I use one product independently?

**Success:** Selects the appropriate product and reaches its installation guide without reading maintainer or implementation instructions first.

**Reading path:** [Project introduction](../README.md) → [product relationships](architecture.md) when needed → the selected product's guide.

## A skill author assessing instructions

**Goal:** Assess a local skill, interpret the findings, revise it, and reassess.

**Already knows:** The skill's intended task and how to edit its files. Can follow Python environment setup instructions.

**Needs explained:** Scanner versus adjudication, provider requirements and data sent, confirmed versus unresolved findings, report scope, and the difference between successful execution and a safety judgment.

**Questions:** What do I install? How do I configure and run assessment? What output should I inspect? Which findings need action? What was not reviewed? How do I check a revision?

**Success:** Produces or locates a report pair, obtains a summary, identifies the next action and assessment limitations, and knows how to reassess after changes.

**Reading path:** [Assessment kit](../products/assessment-kit/README.md), followed by [governance](../GOVERNANCE.md) when proposing a change to the supplied skills.

## An operator sharing a catalog

**Goal:** Deploy the supplied example or publish a maintained catalog of the team's own skills.

**Already knows:** Basic Git and CLI use. Can arrange GitLab project, runner, registry, and provider access with the relevant administrators.

**Needs explained:** Prebuilt versus Operator responsibilities, the assessment-to-site flow, matching skill content and evidence, publication behavior, evidence retention, and component ownership during updates.

**Questions:** Which deployment mode fits? What access and configuration are required? How do I verify the site and downloads? Does a negative assessment block publication? What must I retain or preserve before another run or update?

**Success:** Follows the selected deployment path, verifies the published catalog and downloads, and understands the ongoing responsibilities of that mode.

**Reading path:** [Architecture](architecture.md) → [Prebuilt installation](../products/deployment-kit/prebuilt/docs/install.md) or [Operator guide](../products/deployment-kit/operator/docs/README.md).

## A contributor changing the platform

**Goal:** Change SkLC source or documentation and validate the contribution.

**Already knows:** Software development and Git. Has no assumed knowledge of SkLC's Python, Astro, or product layout.

**Needs explained:** Component responsibilities, consumer artifacts versus maintainer tooling, required development tools, generated-data boundaries, and relevant checks.

**Questions:** Where does this change belong? What must I install? Which checks validate it? Which files are generated? How do I avoid changing assessment evidence while building the site?

**Success:** Locates the owning component, completes development setup, runs applicable checks, and proposes a focused change with appropriate documentation.

**Reading path:** [Architecture](architecture.md) → [Contributing](../CONTRIBUTING.md) → [lint setup](linting.md) and task-relevant references.
