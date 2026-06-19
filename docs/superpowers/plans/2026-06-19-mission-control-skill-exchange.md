# Mission Control Skill Exchange Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply the Mission Control theme and fix the highest-value non-CI review findings for the static skill exchange.

**Architecture:** Keep Python responsible for validation, scanner ingestion, generated records, BOE, and zip packaging. Keep Astro static pages with React only for catalog and scanner-run interactivity. Add small utility boundaries where needed instead of broad rewrites.

**Tech Stack:** Python 3.12+, pytest, Astro, React, TypeScript, Node scripts.

---

## Files

- Modify `.gitignore` to ignore local visual companion state.
- Modify `scripts/skill_exchange/exchange_builder.py` for index contract, validation blocking, and scanner fallback.
- Modify `scripts/skill_exchange/boe.py` for provenance fields.
- Modify `scripts/skill_exchange/zipper.py` for package safety.
- Modify `site/scripts/copy-downloads.mjs` for path containment.
- Modify `site/src/pages/skills/[namespace]/[skillId].astro` for safer Markdown rendering and detail layout.
- Modify `site/src/components/SkillCatalog.tsx` for Mission Control catalog UX.
- Modify `site/src/components/RecommendationBadge.astro` and `site/src/styles/global.css` for recommendation labels and theme.
- Modify tests under `tests/` with focused behavior coverage.
- Modify `site/package.json` and `site/package-lock.json` for the Astro patch update.

## Tasks

### Task 1: Generated Contract And Scanner Fallback

- [ ] Write tests in `tests/test_build_exchange.py` proving generated records include `risk`, `risk_reason`, scanner provenance, canonical BOE path, and recommendation.
- [ ] Write tests proving a scanner failure creates an `Unknown` record when display policy allows unknowns.
- [ ] Implement a scanner fallback report path in `build_exchange()`.
- [ ] Include `risk`, `risk_reason`, `scanner_provenance`, `latest_source_commit_sha`, and canonical `boe_path` in records.
- [ ] Run `uv run --extra test pytest tests/test_build_exchange.py -q`.

### Task 2: Validation Blocking

- [ ] Write a test proving invalid required metadata blocks publication output.
- [ ] Implement validation-error blocking before scanner, zip, detail, and index output.
- [ ] Run `uv run --extra test pytest tests/test_validation.py tests/test_build_exchange.py -q`.

### Task 3: Artifact And Zip Safety

- [ ] Write tests for unsafe scanner artifact copy paths in a Node test script or Python subprocess harness.
- [ ] Write tests proving zips reject symlinks and preserve expected package layout.
- [ ] Implement realpath containment checks in `copy-downloads.mjs`.
- [ ] Implement symlink rejection and file count/size caps in `zipper.py` and hashing where appropriate.
- [ ] Run targeted tests.

### Task 4: Markdown Safety

- [ ] Write a test or build fixture proving raw `<script>` and event-handler HTML do not appear in built detail pages.
- [ ] Disable or sanitize raw HTML rendering from skill Markdown.
- [ ] Run the targeted test and `npm --prefix site run build`.

### Task 5: Mission Control UI

- [ ] Update catalog and detail labels: `Skill Instructions`, `Download skill package`, `Safe to use`, `Use caution`, `Avoid installing`.
- [ ] Add a trust snapshot using existing generated fields only.
- [ ] Replace the visual system with the Mission Control theme: dark canvas, cyan network accents, glass panels, strong action hierarchy, responsive layouts.
- [ ] Fix tab and scanner row accessibility with button-based controls where practical.
- [ ] Run `npm --prefix site run build`.

### Task 6: Dependency Patch And Final Verification

- [ ] Update Astro to the latest non-major patch supported by the existing dependency set.
- [ ] Run `npm --prefix site install`.
- [ ] Run `uv run --extra test pytest`.
- [ ] Run `npm --prefix site run build`.
- [ ] Run `git status --short --ignored` and commit the completed change.

