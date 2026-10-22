# Skill Exchange Governance

Human contributors own skill content and assessment decisions. Maintainers approve changes after human review. Assessment results provide review context; they do not replace that review.

## Existing evidence

Current paired reports under `products/skill-catalog-assessments/` preserve the latest assessment; Git preserves earlier results. Do not hand-author or alter those results to make a build pass.

The site builder requires exact content freshness through the shared public package hash, successful native execution, completed adjudication, and one matching determination per finding. Missing, stale, or mismatched evidence fails generation. Nonfatal partial coverage and negative safety judgments are advisory and remain visible with their reasons.

The assessment kit owns execution and report interpretation; upstream and customer CI invoke its public commands. A new or changed skill cannot enter the assessed site without matching evidence; the separate skill-catalog download contains skill files without an assessment requirement.

## Review and generated files

- Contributors propose skill and application changes by pull request.
- At least one human reviewer inspects skill changes before a maintainer merges them.
- Reviewers consider declared purpose, metadata, instructions, supporting files, and available assessment evidence.
- Skill packages declare their existing name and description in `SKILL.md`; the catalog uses these alongside the full instructions.
- The index, copied assessment JSON pairs, and skill ZIPs are derived site inputs. Generate them locally or in CI; do not commit them.
- Keep credentials and environment-specific deployment settings outside the repository.
