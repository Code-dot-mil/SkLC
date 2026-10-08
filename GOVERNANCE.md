# Skill Exchange Governance

Human contributors own skill content and exchange policy. Maintainers approve changes after human review. Assessment results provide review context; they do not replace that review.

## Existing evidence

BOE bundles under `.exchange/generated/boe/` preserve evidence from earlier protected assessment runs. Do not hand-author or alter those results to make a build pass.

The site builder verifies matching skill content, companion-file hashes, scanner identity and configuration, and report completeness before using a bundle. Missing or invalid evidence fails site generation. Existing static-only and LLM-assisted results remain distinguishable by scan mode and confidence flags.

Assessment execution and automated evidence publication are currently absent. The [roadmap](docs/roadmap.md) describes the intended replacement. A new or changed skill cannot enter the assessed site without matching evidence; the separate skill-catalog download contains skill files without an assessment requirement.

## Review and generated files

- Contributors propose skill, policy, and application changes by pull request.
- At least one human reviewer inspects skill changes before a maintainer merges them.
- Reviewers consider declared purpose, metadata, instructions, supporting files, and available assessment evidence.
- Unknown categories and tags produce validation warnings; maintainers decide whether those values are useful.
- Indexes, tables, skill records, scanner-run mirrors, and ZIPs are derived site inputs. Generate them locally or in CI; do not commit them.
- Keep credentials and environment-specific deployment settings outside the repository.
