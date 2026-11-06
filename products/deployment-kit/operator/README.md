# Operator build runtime

The Python runtime builds catalog data from skill packages and their existing assessment pairs. It runs no scanner or provider during generation and writes no assessment evidence. The Operator site serves catalog filters, tags, sorting, full instructions, adjudication guidance, original scanner findings, and JSON downloads.

Install this product alongside a released assessment-kit wheel. Its package metadata declares `skill-assessment` and PyYAML; it does not resolve sibling source directories or maintainer tooling. Product tests include their own fixtures.

The assessment kit owns package hashing (`skill_digest`), current-pair eligibility (`is_current_assessment`), and CLI action summaries (`summarize`). Generation uses the public hash and eligibility interfaces, then projects only fields consumed by the existing native scanner display. Safety labels come from completed adjudication, independently of scanner risk. The site summary contains adjudication only; the assessment CLI retains its action summary. Generation requires a successful current LLM-assisted pair for each selected skill; negative judgments and advisory partial coverage remain publishable.

In an Operator instance, `python -m skill_exchange.cli assess-catalog` assesses `skills/<skill>/` into `evidence/<skill>/`, reusing current reports by default. Add `--force` to reassess every skill. `generate` reads those pairs to build `.exchange/generated/`. Both commands accept `--skills`, `--evidence`, and `--generated`. Skill basenames must be globally unique because evidence is stored by basename. Source content and matching evidence stay together.

Upstream Prebuilt generation uses the same CLI with explicit inputs:

```sh
python -m skill_exchange.cli generate --skills products/skill-bundle \
  --evidence products/skill-bundle-assessments --generated products/deployment-kit/operator/.exchange/generated
```

Node always consumes `.exchange/generated/` beside the `site/` directory, resolved from the site's Astro root. The index supplies identity, description, instructions, package download paths, adjudication, disposition counts, native display rows, and `assessment_downloads` for the two JSON reports. Scope and limitations follow the adjudication summary. Generation copies reports under `assessments/<skill>/` and creates individual skill archives under `zips/`.
