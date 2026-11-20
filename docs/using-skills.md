# Using a skill

A skill gives an AI agent reusable instructions for a task. An AI agent is an application that can follow instructions and use tools to carry out work. You supply your goal and the information it needs; the skill describes a process for the agent to follow. You still need to review the result.

For example, a team could write a skill to check whether a draft report covers an agreed checklist. Instead of explaining the checklist in every request, someone could ask the agent to use that skill on a draft. This is an example of how skills can help; SkLC's supplied bundle contains skills for software tasks.

## Start by reading

You do not need to install SkLC or run commands to learn about a skill. If your team has a **Skill Exchange**, open that website to browse descriptions, read instructions and assessment results, and download skills. Ask the person who shared SkLC whether your team has an exchange to browse. This repository contains the tools for creating one, rather than a running exchange you must sign up for.

To see what is supplied here, read the [bundle's four skill descriptions](../products/skill-bundle/README.md). They cover Python code review, unit tests, inline documentation, and change descriptions. Choose based on the task you need help with; these packages may not fit your work.

## Check whether you can use it

A skill is a package of instructions, sometimes with scripts, examples, or other supporting files. Its main instruction file is named `SKILL.md`; it is a text document you can read. The package is used by an agent application, rather than an application you can run by itself.

Before downloading or installing a skill, answer these questions:

- **Does it fit your task?** Read its purpose, expected inputs, and the result it is meant to produce.
- **Can your application use it?** Check whether your agent supports this skill format and where it expects skill packages. Support and installation steps vary between applications; a chat application's ability to accept text does not establish skill support.
- **What else does it need?** Check for required applications, accounts, files, and permissions. If these are unclear, ask the skill's author or your team's support contact before using it.
- **Can you use it with your information?** Follow your organization's rules for the AI application and the information you provide. Check what the skill asks the agent to access or do.

If you do not already have an agent application, ask your team which one is appropriate for your work and supports the skill you chose. Share the skill's description and requirements with the person helping you. You do not need to set up a website or assessment tools just to use a skill.

## Read the assessment, when available

An assessment looks for potential problems in the skill's instructions. On an exchange, read the findings and the review's limitations alongside the skill. A confirmed finding is a problem the review supports; an unresolved finding still needs investigation. A false positive is an alert the contextual review dismissed. Missing or incomplete coverage means some questions remain unanswered.

An assessment helps you decide what needs attention. It does not guarantee that a skill is suitable for your task or that its results will be correct. SkLC's contextual review examines the main instruction file and scanner evidence; it does not independently review supporting files. Ask the author or your team's reviewer about concerns you cannot evaluate yourself.

If you have downloaded SkLC's assessment results instead of reading them on an exchange, open `summary.md` in the directory named for your skill. The [assessment results guide](../products/skill-bundle-assessments/README.md) explains the archive layout and findings. Reading the included summaries requires no assessment tools or new scan.

## Install and try a task

Once you have chosen a suitable skill and compatible agent, follow the agent's installation instructions. For SkLC's supplied packages, you can use the Skills command-line tool (`npx skills add`) or copy complete folders from a downloaded ZIP. Keep supporting files with each skill. The [bundle installation guide](../products/skill-bundle/README.md) explains both methods, the software you need, and how to choose a version. If the guide's commands are unfamiliar, ask a technical colleague to help with setup.

Confirm that the agent recognizes the installed skill. Then try a small task whose result you can check. Name the skill in your request and explain the outcome you want. For the report-checking example, that might be: “Use the report-checking skill on this draft and list any checklist items it does not cover.”

Review the result against the original information and your goal before relying on it. Check any proposed action before allowing the agent to carry it out. If the skill misses something or produces an incorrect result, record what you asked, what happened, and what you expected, and share that feedback with its maintainer. Changes to a skill or the agent can change its behavior, so check again when either is updated.

To understand how teams create, check, share, and maintain skills, return to the [skill lifecycle](../README.md#the-skill-lifecycle).
