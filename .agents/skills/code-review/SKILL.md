---
name: code-review
description: "Review a branch, PR, uncommitted work, or changes since a named revision against repository standards and the originating task. Scale review depth to the change and report both perspectives separately."
---

Two-axis review of committed and local changes since a fixed point:

- **Standards**: does the code conform to this repo's documented coding standards?
- **Spec**: does the code faithfully implement the originating issue / spec?

Keep the two perspectives distinct. Use one review pass for small, clear changes;
use separate reviewers when complexity, uncertainty, or the user's request warrants
independent passes.

Use the supplied issue, task text, or local specification. Fetch referenced issues with available tracker tools; no separate tracker-setup skill is required.

## Process

### 1. Pin the fixed point

Whatever the user said is the fixed point (a commit SHA, branch name, tag, `main`, `HEAD~5`, etc.). For local work without a supplied fixed point, use `HEAD`.

Resolve the fixed point to a commit SHA and pin its merge-base with `HEAD` using `git merge-base <fixed-point> HEAD`. Capture `git diff <merge-base>` to include committed, staged, and unstaged tracked changes. Also note the commit list via `git log <merge-base>..HEAD --oneline`.

Inventory untracked files with `git ls-files --others --exclude-standard -z`; include their full contents, or binary metadata, in the review. Apply any supplied task-path scope to both tracked and untracked changes. Do not stage files to make them visible.

Before going further, confirm the fixed point resolves and either the tracked diff or untracked inventory contains changes in scope. Report an invalid ref or no changes before reviewing. Use the same pinned comparison and untracked inventory for each perspective; do not change the worktree during review.

### 2. Identify the spec source

Look for the originating spec, in this order:

1. An issue, task text, or path the user supplied.
2. Issue references in commit messages (`#123`, `Closes #45`, GitLab `!67`, etc.), fetched with available tracker tools.
3. A spec file under `docs/`, `specs/`, or `.scratch/` matching the branch name or feature.
4. If nothing is found, ask for the originating task or spec. If none is available, skip the Spec perspective and report "no spec available".

Include later accepted decisions, acceptance checks, behavior to preserve, and
exclusions with the originating task. When an older specification conflicts with
a later accepted decision, identify the conflict and review against the current
decision. Surface unresolved conflicts rather than inventing requirements.

### 3. Identify the standards sources

Search the repo for every file that documents how code should be written. When `CODING_STANDARDS.md` or `CONTRIBUTING.md` exists, it must be on the list.

Use code smells to investigate a concrete problem. Explain the correctness or
maintenance consequence and recommend the smallest sufficient correction.
Introducing a type, abstraction, helper, or polymorphism requires a demonstrated
benefit within the current task. Label judgment calls as such; documented
repository standards take precedence. Skip matters already enforced by tooling.

### 4. Review at the appropriate depth

For small, clear changes, review both perspectives in one pass. For consequential
complexity or uncertainty, use separate Standards and Spec reviewers with the
available native subagent tools. Honor explicit user choices about review depth
and model; otherwise use the host's configured defaults. Respect host restrictions
and report any limitation on requested independent review.

Reviewers inspect only; they must not edit, commit, push, create PRs, or update issues.

Give each reviewer or review pass:

- The pinned diff command, commit list, task-path scope, and untracked inventory
  with contents or binary metadata.
- The originating task, later accepted decisions, acceptance checks, preserved
  behavior, exclusions, and relevant specification sources from step 2.
- The standards sources and judgment guidance from step 3.

**Standards perspective:** Inspect assertions and failure paths against the
repository's current contracts. Cite the rule, affected lines, and concrete
consequence for each demonstrated violation. Distinguish documented violations
from judgment calls and recommend the smallest sufficient correction.

**Spec perspective:** Identify missing or partial requirements, unrequested
behavior, and incorrect implementations of current requirements. Cite the task
or accepted decision for each finding. If there is no spec source, report that
this perspective could not be assessed.

### 5. Aggregate

Present findings under `## Standards` and `## Spec` headings. Preserve that separation whether one review pass or separate reviewers produced them. Report the review depth, models used for delegated reviews, and any limitations.

End with a one-line summary: total findings per axis, and the worst issue _within each axis_ (if any). Don't pick a single winner across axes: that's the reranking the separation exists to prevent.

## Why two axes

A change can pass one axis and fail the other:

- Code that follows every standard but implements the wrong thing → **Standards pass, Spec fail.**
- Code that does exactly what the issue asked but breaks the project's conventions → **Spec pass, Standards fail.**

Reporting them separately stops one axis from masking the other.

Adapted from [Matt Pocock's code-review skill](https://github.com/mattpocock/skills/blob/49dd158d1076134a641b33efb035946536778336/skills/engineering/code-review/SKILL.md). Licensed under [MIT](LICENSE).
