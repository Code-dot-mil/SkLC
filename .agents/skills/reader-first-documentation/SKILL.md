---
name: reader-first-documentation
description: Use when creating or substantially revising user-facing software documentation, including READMEs, onboarding, task guides, reference, architecture explanations, or documentation reading order. Not for code comments, agent instructions, or prose-only copyediting.
---

# Reader-first documentation

Write documentation that lets its intended reader understand the purpose, choose a path, complete a task, and interpret the outcome without the author's conversation context. Reuse established audience knowledge and perform editorial work autonomously.

## Establish the reader and source

Identify the requested repository and revision before writing. For a requested branch or release, verify that source rather than assuming the current checkout matches. Preserve unrelated work.

Start with [SkLC's reader profiles](../../../docs/PERSONAS.md), its documentation entry points, and the source of documented behavior. Reuse the accepted audience priority and knowledge baseline across documents. If a new audience or a material profile change is needed, read [audience profiles](references/audience-profiles.md) before updating `docs/PERSONAS.md`.

Research first. If consequential audience or product-intent gaps remain, ask one consolidated intake and save the answers. Carry accepted answers forward across documents. Infer routine editorial choices; label unconfirmed assumptions. Ask again only when a new material conflict or missing fact cannot be resolved from available evidence. Never require outline, section, or draft approval unless the user requests it. Continue independent work while a required answer is pending; do not treat silence as agreement.

## Choose the document's job

Select its primary reader, question, and successful outcome. Use the appropriate form without forcing a four-part template or directory structure:

| Reader needs                                    | Form         |
| ----------------------------------------------- | ------------ |
| Learn through a first successful experience     | Tutorial     |
| Complete a specific task                        | How-to guide |
| Look up exact behavior or settings              | Reference    |
| Understand purpose, relationships, or tradeoffs | Explanation  |

Entry points can route between forms. Order links around reader decisions and prerequisites. Keep reference details reachable without interrupting the first-use path. Modify the smallest coherent documentation scope; report wider gaps rather than silently rewriting the corpus.

## Draft and verify

Explain the problem and intended outcome before implementation machinery. Introduce unfamiliar terms where needed. Put prerequisites and consequential limitations before the actions or decisions they affect. Pair commands with working-directory context, expected results, and next actions. Use authentic output when available; label illustrative examples and avoid invented fields or guarantees.

Keep each paragraph accountable to a reader question. A rule earns space through its practical consequence or rationale. Put contributor and agent implementation rules in their own guidance. Remove repeated caveats, historical workflow disputes, and internal mechanisms that do not help this reader. Distinguish current capability, planned work, and historical decisions.

Check claims against source, configuration, supported interfaces, or authoritative documentation. Verify links in the layout where readers will use them, including packaged layouts when relevant. Prefer existing focused checks; distinguish inspected examples from commands actually executed. Document uncertainties without inventing product policy or rationale.

## Test the reading experience

For new guides or substantial restructuring, follow [fresh-reader testing](references/fresh-reader-testing.md). Use an independent agent with only the proposed reading path and relevant persona when delegation is available. Revise demonstrated gaps and repeat the affected questions. For small edits or unavailable delegation, perform a bounded walkthrough and disclose that it was not an independent test.

Present the completed result, material decisions, validation, and unresolved limitations. A successful reader test supports comprehension; technical accuracy still requires source verification.

## Sources

These independently written instructions adapt audience and document-type selection from [GitHub's documentation-writer](https://github.com/github/awesome-copilot/blob/main/skills/documentation-writer/SKILL.md), fresh-reader testing from [Anthropic's doc-coauthoring](https://github.com/anthropics/skills/blob/main/skills/doc-coauthoring/SKILL.md), and the [Diátaxis framework](https://diataxis.fr/). Recurring interviews and approval gates are replaced with persistent reader profiles and autonomous drafting. The upstream skills are not runtime dependencies.
