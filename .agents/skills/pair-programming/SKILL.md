---
name: pair-programming
description: Use when the user requests pair programming, a managing agent with implementation partners, or delegated coding with native subagents.
metadata:
  internal: "true"
  mitre.version: "0.1.0"
  mitre.category: Productivity
  mitre.tags: delegation,pair-programming,subagents
---

# Pair programming

Delegate meaningful implementation work early. The managing agent plans, coordinates, reviews and verifies; implementers build and improve the solution. Preserve the user's model choices and normal authorization boundaries.

## Choose the implementer

Use the environment's native subagent tools. Honor explicitly selected models without substitution. If native delegation is unavailable, explain that limitation.

Give native implementers the relevant task, repository context, applicable skills, acceptance criteria, and authority to inspect, edit and test. Respect available agent tools and host restrictions.

## Work together until the task is complete

- Plan cohesive assignments with clear ownership and acceptance criteria. Give enough context to reason about contracts and tests; avoid both vague handoffs and prescribing every implementation decision. Do not implement everything first and ask the partner to duplicate it.
- Let the implementer inspect or request missing context. Use focused assignments when the work has separable parts, rather than forcing the whole application into one response.
- Review contributions and run meaningful checks. Send concrete failures, review findings and relevant updated files back to the implementer. Continue the same assignment through revisions. The manager should not absorb all repair work after the first imperfect response. Handle integration and cross-cutting decisions directly when useful, explaining material manager corrections.
- Allow time and output appropriate to the selected model and task. Do not optimize for the fewest requests, force tiny output limits, or treat a slow model as failed merely because a tool call yielded. Use asynchronous execution and periodic progress updates for long requests.
- Stop when acceptance is met, the user redirects, or evidence shows the current approach cannot make progress. Diagnose repeated failures or unclear outcomes before repeating work; no unbounded blind retries.

Report what the implementer contributed, manager corrections, checks and remaining limitations. Pairing continues on relevant follow-ups until the user changes direction; preserve model, ownership and current state across handoffs.
