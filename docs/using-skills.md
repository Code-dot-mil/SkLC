# Choose and download a SkLC skill

An AI agent is an application that can follow instructions and use tools to carry out work. A skill gives an AI agent reusable instructions for a task. You supply your goal and the information it needs; the skill describes a process for the agent to follow. You still need to review the result.

For example, a unit-test skill can tell an agent how to propose tests for a change. You can refer the agent to the changed code without repeating the testing process in each request.

## What you need to use a skill

You need an agent application that supports skills and is approved for your work. A skill is a package of instructions, sometimes with scripts, examples, or other supporting files. Its main instruction file is named `SKILL.md`. You do not need to set up a website or assessment tools just to use a skill.

Before downloading or installing a skill, answer these questions:

- **Does it fit your task?** Read its purpose, expected inputs, and the result it is meant to produce.
- **Can your application use it?** Check whether your agent supports this skill format and where it expects skill packages. Support and installation steps vary between applications; a chat application's ability to accept text does not establish skill support.
- **What else does it need?** Check for required applications, accounts, files, and permissions. If these are unclear, ask the skill's author or your team's support contact before using it.
- **Can you use it with your information?** Follow your organization's rules for the AI application and the information you provide. Check what the skill asks the agent to access or do.

## Where to find skills

You do not need to install anything or run commands to learn about a skill. If your organization has a **Skill Exchange**, open it to browse skill descriptions, read instructions and assessment results, and download skills. If your organization wants to set up its own exchange, SkLC provides the tools.

The supplied skills cover Python code review, unit tests, inline documentation, and change descriptions. Choose based on the task you need help with; these packages may not fit your work.

## Read a skill’s security assessment

An assessment looks for potential problems in the skill's instructions. On the skill’s detail page, open **Assessment Evidence** to read the findings and the review's limitations. A confirmed finding is a problem the review supports; an unresolved finding still needs investigation. A false positive is an alert the contextual review dismissed. Missing or incomplete coverage means some questions remain unanswered.

An assessment helps you decide what needs attention. It does not guarantee that a skill is suitable for your task or that its results will be correct. SkLC's contextual review examines the main instruction file and scanner evidence; it does not independently review supporting files. Ask the author or your team's reviewer about concerns you cannot evaluate yourself.

To get the supplied reports and open a skill’s summary, follow the [assessment results guide](../products/skill-bundle-assessments/README.md). To scan your own skill, follow the [assessment kit guide](../products/assessment-kit/README.md).

## Install and try a task

On the exchange, open the skill's detail page, select **Download skill package**, and extract the ZIP. Once you have chosen a suitable skill and compatible agent, follow the agent's installation instructions. Keep the complete skill folder together, including supporting files. If you want the supplied skills together, follow the [bundle installation guide](../products/skill-bundle/README.md).

Confirm that the agent recognizes the installed skill. Then try a small task whose result you can check. Name the skill in your request and explain the outcome you want. For example, ask “Use the unit-test-generation skill to propose tests for this function.” AI4SDLC’s [Unit Testing with GenAI guide](https://code-dot-mil.github.io/AI4SDLC/plays/testing-types/unit-testing/) explains how to review those tests.

Review the result against the original information and your goal before relying on it. Check any proposed action before allowing the agent to carry it out. If the skill misses something or produces an incorrect result, record what you asked, what happened, and what you expected. Changes to a skill or the agent can change its behavior, so check again when either is updated.

If your agent supports project-level skills, keep the complete skill folder in your project repository so your team can review and version changes together. For guidance on deciding what an agent may do in your team's workflow, see AI4SDLC’s [AI Workflow Design play](https://code-dot-mil.github.io/AI4SDLC/plays/ai_sdlc_workflows-play/).
