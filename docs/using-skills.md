# Choose and download a SkLC skill

You can read a skill’s instructions and assessment on your organization’s Skill Exchange before installing anything. To use the skill, you need an agent approved for your work that supports the skill’s format.

## Choose a skill

If your organization has an exchange, browse its catalog for your task. Open a skill’s detail page and read **Skill Instructions**. You can also find the supplied skills in the [bundle guide](../products/skill-bundle/README.md). Use these questions to decide whether to download a skill.

- **Does it fit your task?** Read its purpose, expected inputs, and the result it is meant to produce.
- **Can your application use it?** Check whether your agent supports this skill format and where it expects skill packages. Support and installation steps vary between applications; a chat application's ability to accept text does not establish skill support.
- **What else does it need?** Check for required applications, accounts, files, and permissions. If these are unclear, ask the skill's author or your team's support contact before using it.
- **Can you use it with your information?** Follow your organization's rules for the AI application and the information you provide. Check what the skill asks the agent to access or do.

## Read the assessment

On the detail page, open **Assessment Evidence**. Read the findings and coverage limits behind the recommendation. A confirmed finding is a problem supported by the review. An alert judged to be a false positive was dismissed during review. If a finding is unresolved or coverage is incomplete, check how that affects your task before using the skill.

To get the supplied reports and open a skill’s summary, follow the [assessment results guide](../products/skill-bundle-assessments/README.md). To scan your own skill, follow the [assessment kit guide](../products/assessment-kit/README.md).

## Install the skill

On the exchange, select **Download skill package**. Extract the ZIP and install the complete folder containing `SKILL.md` in the location your agent documents. Keep any supporting files with it. Confirm the skill appears in your agent’s list of installed skills.

If you want the supplied skills together, the [bundle guide](../products/skill-bundle/README.md) lists the contents and explains how to verify and install that download.

For example, after installing `unit-test-generation`, ask your agent, “Use unit-test-generation to propose tests for this function.” AI4SDLC’s [Unit Testing with GenAI guide](https://code-dot-mil.github.io/AI4SDLC/plays/testing-types/unit-testing/) explains how to review those tests. Its [AI Workflow Design play](https://code-dot-mil.github.io/AI4SDLC/plays/ai_sdlc_workflows-play/) covers how to decide what an agent may do in your team’s workflow.
