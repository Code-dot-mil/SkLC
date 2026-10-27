# Deployment site

This Operator Astro site serves skill instructions, adjudication, and original scanner evidence. Its catalog supports text search, categories, tags, recommendation filters, and sorting. Safety labels come only from completed adjudication.

Run commands from this site directory after installing dependencies with `npm ci`. Set `SKILL_EXCHANGE_GENERATED_ROOT` to the absolute path of generated site data before running `npm run build` or `npm run dev`. Generation is a separate Operator CLI step; the Node build consumes its output. Run `npm run lint`, `npm run lint:code`, `npm run typecheck:astro`, and `npm test` to validate site changes. From the upstream checkout root, `just site-lint` runs all three static checks.

`npm run build` copies generated downloads through its `prebuild` hook. Before starting `npm run dev` on a fresh checkout, run `npm run prebuild` with the same generated-data environment variable. Repeat that copy step when regenerated skill ZIPs or assessment downloads change; the development server does not copy them automatically.

The generated `index.json` supplies each skill's adjudication summary, status, coverage judgment, dispositions, and scope, alongside skill content and catalog metadata. Native run/finding/artifact rows preserve the original scanner display; paired false positives are annotated by ordered index and rule identity. `assessment_downloads.skillspector` and `assessment_downloads.adjudication` supply the two original report downloads. JSON reports live under `assessments/<skill>/` and skill archives under `zips/`; the site copies these to relative public download paths for root or nested hosting.

Consumers who customize this directory own the entire site component, including its future updates.
