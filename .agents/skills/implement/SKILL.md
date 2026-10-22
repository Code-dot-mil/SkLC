---
name: implement
description: "Implement a piece of work based on a spec or set of tickets."
---

# Implement

Implement the work described by the user in the spec or tickets.

Record the starting `HEAD` and existing local changes. Preserve unrelated edits and identify the paths belonging to this task.

If the user passes a ticket reference, fetch it from the issue tracker and state its title before starting. If the reference is ambiguous, ask.

Before editing, establish the outcome, acceptance checks, behavior to preserve, and exclusions from the originating task and later accepted decisions. Inspect the relevant source and revision before proposing missing functionality. Resolve conflicts with older specifications explicitly.

Use the `tdd` skill where available, at pre-agreed seams; otherwise follow the repository's behavior-testing guidance.

After the smallest complete path works, inspect the cumulative diff before expanding it. Remove additions without a current requirement. Resolve material scope growth before continuing.

Run configured typechecking and affected tests after relevant changes, and the applicable full test suite once at completion. Reuse passing results while their inputs remain unchanged unless new evidence questions them.

Once done, use the sibling [code-review skill](../code-review/SKILL.md) with the starting `HEAD`, originating task, later accepted decisions, acceptance checks, preserved behavior, exclusions, and task paths. Address findings with focused changes, rerun affected checks, and review the corrected diff.

After checks and review, commit only the reviewed task changes to the current branch. Report the commit, outcome, acceptance evidence, manually reviewed diff size, review findings, and remaining limitations. Distinguish automated checks from workflows actually exercised. Do not push. Do not create a PR or update the issue unless the user explicitly requests those actions.

Adapted from [Matt Pocock's implement skill](https://github.com/mattpocock/skills/blob/49dd158d1076134a641b33efb035946536778336/skills/engineering/implement/SKILL.md). Licensed under [MIT](LICENSE).
