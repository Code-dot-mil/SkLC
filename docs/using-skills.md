# Using a skill

An AI agent is an application that can follow instructions and use tools to carry out work. A skill gives an agent reusable instructions for a task. You supply your goal and the information it needs. The skill describes a process for the agent to follow, and you review the result.

For example, a unit-test skill can tell an agent how to propose tests for a change. When you ask the agent to use the skill, you can refer it to the changed code without repeating the testing process in each request.

## What you need to use a skill

You need an agent application that supports skills and is approved for your work. A skill package contains a text file named `SKILL.md` and may include scripts, examples, or other supporting files. The agent reads the skill instructions when you use it for a task.

Before downloading or installing a skill, answer these questions:

- **Does it fit your task?** Read its purpose, expected inputs, and the result it is meant to produce.
- **Can your application use it?** Check whether your agent supports this skill format and where it expects skill packages. Support and installation steps vary between applications; a chat application's ability to accept text does not establish skill support.
- **What else does it need?** Check for required applications, accounts, files, and permissions. If these are unclear, ask the skill's author or your team's support contact before using it.
- **Can you use it with your information?** Follow your organization's rules for the AI application and the information you provide. Check what the skill asks the agent to access or do.

## Where to find skills

You can browse skills and read their instructions without installing software or running commands. If your organization has a **Skill Exchange**, open it to browse descriptions, read instructions and assessment results, and download skills. SkLC provides tools your organization can use to set up its own exchange.

The supplied skill bundle includes examples for Python code review, unit tests, inline documentation, and change descriptions. Choose a skill that fits the task you want help with.

## Use assessment results when choosing a skill

An assessment looks for potential problems in the skill's instructions. On an exchange, read the findings and the review's limitations alongside the skill. A confirmed finding is a problem the review supports; an unresolved finding still needs investigation. A false positive is an alert the contextual review dismissed. Missing or incomplete coverage means some questions remain unanswered.

An assessment helps you decide what needs attention. It does not guarantee that a skill is suitable for your task or that its results will be correct. SkLC's contextual review examines the main instruction file and scanner evidence; it does not independently review supporting files. Ask the author or your team's reviewer about concerns you cannot evaluate yourself.

See the [assessment results guide](../products/skill-bundle-assessments/README.md) for help with downloaded reports. To assess a skill yourself, use the [assessment kit](../products/assessment-kit/README.md).

## Install and try a task

Open the skill's detail page on the exchange and download its ZIP. Extract it and follow your agent's instructions for installing a skill. Keep the complete skill folder together, including any supporting files. If you downloaded the supplied bundle, follow the [bundle installation guide](../products/skill-bundle/README.md).

Confirm that the agent recognizes the installed skill. Then try a small task whose result you can check. Name the skill in your request and explain the outcome you want. For example, ask “Use the unit-test-generation skill to propose tests for this function.” Review the proposed tests and run them before relying on them.

Review the result against the original information and your goal before relying on it. Check any proposed action before allowing the agent to carry it out. If the skill misses something or produces an incorrect result, record what you asked, what happened, and what you expected. Check the skill again when its instructions or the agent change.

If your agent supports project-level skills, keep the complete skill folder in your project repository so the team can review and version changes together. The [skill lifecycle](../README.md#the-skill-lifecycle) explains how teams create, check, share, and maintain skills.
