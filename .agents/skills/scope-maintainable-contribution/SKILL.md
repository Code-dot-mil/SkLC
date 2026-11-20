---
name: scope-maintainable-contribution
description: Use when turning a software request, roadmap milestone, or oversized change into maintainable, reviewable implementation tasks. Not for routine edits with settled scope or code review focused on defects.
metadata:
  internal: "true"
---

# Scope Maintainable Contributions

Apply a maintainer's judgment before expanding a request into architecture or task prompts. Optimize for the smallest complete customer outcome and its ongoing maintenance cost. Simplify the solution before splitting it.

## Establish the contribution

Inspect relevant repository instructions, requirements, existing implementation, and tests. Find what can be reused. Distinguish user requirements from inherited design choices, optional features, and agent-proposed machinery.

State the observable outcome, acceptance checks, preservation requirements, and exclusions. Question requirements that do not serve the outcome. Surface conflicts with existing specs; propose precise amendments rather than silently ignoring or rewriting them. Ask only about unresolved decisions that materially affect correctness or scope. Honor decisions and authorization already given.

For a clear, low-risk task, produce one short task prompt. Spend more time on design only for consequential uncertainty, such as a public interface, persistent format, migration, or cross-product dependency. Describe the decision and tradeoffs. A new architecture is not a prerequisite.

Choose the appropriate result: proceed directly, decompose the contribution, resolve a design decision first, or recommend deferring work whose benefit does not justify its cost.

## Bound maintenance and review effort

Require each new dependency, schema, abstraction, configuration option, compatibility branch, automation helper, and document to serve an acceptance criterion or binding requirement. Prefer existing mechanisms. Optional output does not automatically require implementing support for it now. Preserve necessary failure handling and current behavior.

Unless the user sets another budget, target a one-hour review and at most 300 manually reviewed changed lines, counting additions and deletions across code, tests, configuration, and documentation. Report generated changes separately, including the inputs and assumptions that still need review. This is a planning target, not a guarantee; conceptual complexity and file spread also matter.

Estimate before coding. If the scope exceeds the budget, simplify or propose coherent slices; do not silently expand or drop requirements. Keep related tests and usage with each behavior. Each slice must leave a working repository and be understandable using existing or already-reviewed context. Splitting unnecessary architecture into small patches does not justify it.

Never meet the budget by compressing readable code, weakening tests, hiding changes, or moving complexity elsewhere.

## Produce executable task prompts

Default to one concise brief in the conversation, roughly 200 words for a simple task. Do not create separate design documents, plans, commits, or review stages merely to perform this workflow.

For each task, include:

- Observable outcome and acceptance checks, including behavior to preserve.
- Explicit exclusions and any unresolved requirement conflict.
- Relevant repository paths and existing implementation to reuse.
- Expected changes and estimated review size.
- Dependencies on earlier tasks, when needed.
- Verification and completion evidence.

Include an execution checkpoint: inspect the cumulative diff after the first working implementation and before expanding it. Remove unjustified additions; resolve scope growth before proceeding. Complete required checks, then report acceptance evidence, actual diff size, and limitations. Passing tests alone does not establish maintainability or complete requirements coverage.

When implementation is already requested and scope is settled, continue within that authorization. When only planning is requested, deliver the prompts without implementing them.
