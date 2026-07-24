# Static Skill Exchange Architecture

## Purpose

This document describes the current static skill-exchange MVP. It distinguishes assessment and durable evidence from the site-specific artifacts that are materialized for GitLab Pages.

## 1. Component Overview

```mermaid
flowchart LR
  skills[/Skill packages/]
  assess(Assessment)
  boe[/BOE/]
  policy[/Exchange policy and site configuration/]
  catalogBuilder(Catalog builder)
  artifacts[/Static catalog artifacts/]
  astroBuilder(Astro builder)
  site[/Published Astro Exchange Site/]
  ci(CI automation)

  skills -->|supplies| assess
  assess -->|produces| boe
  skills -->|supplies| catalogBuilder
  boe -->|supplies| catalogBuilder
  policy -->|configures| catalogBuilder
  catalogBuilder -->|materializes| artifacts
  artifacts -->|feeds| astroBuilder
  astroBuilder -->|publishes| site
  ci -. runs .-> assess
  ci -. runs .-> catalogBuilder
  ci -. runs .-> astroBuilder

  subgraph legend[Legend]
    component(Component or process)
    output[/Product, evidence, or generated artifact/]
    trigger{{Trigger or event}}
  end
```

Assessment produces BOE from skill packages. Skill packages and BOE independently feed the catalog builder, which produces static catalog artifacts. The Astro builder bakes those artifacts into the published Astro Exchange Site.

## 2. Assessment Internals

```mermaid
flowchart LR
  package[/Skill package/]
  discover(Discover and hash package)
  validate(Validate metadata and policy)
  scan(SkillSpector scan)
  report[/Native scanner report/]
  risk[/Normalized risk and confidence/]

  package -->|supplies| discover
  discover -->|identifies| validate
  validate -->|valid: authorizes| scan
  scan -->|emits| report
  report -->|informs| risk
  validate -->|invalid: skips| rejected[/Excluded from scan/]
```

This layer includes package discovery, content hashing, validation, SkillSpector invocation, and the exchange risk mapping. Merge-request review uses the same core assessment inputs, but produces reviewer context rather than official evidence.

## 3. Evidence Creation and Reuse

```mermaid
flowchart TD
  identity[/Skill content hash plus scan cache key/]
  existing{Matching BOE exists?}
  reuse(Read BOE and native report)
  scan(Run scanner)
  assess(Assess report)
  write(Write BOE bundle)
  bundle[/BOE bundle/]

  identity -->|checks| existing
  existing -->|match: reuses| reuse
  reuse -->|supplies| assess
  existing -->|miss: runs| scan
  scan -->|emits| assess
  assess -->|prepares| write
  write -->|writes| bundle

  subgraph bundleContents[Durable BOE contents]
    boejson[/boe.json/]
    native[/skillspector.json/]
    summary[/summary.json/]
    scannerConfig[/scanner-config.json/]
    hashes[/hashes.json/]
  end
```

The BOE bundle is the durable scanner artifact and evidence bundle. Its matching key lets later publication reuse the recorded scanner evidence and recreate downstream disposable output/artifacts without calling the scanner again.

| File | Purpose |
|---|---|
| `boe.json` | BOE identity, provenance, scan key, selected risk result, and references to companion files. |
| `skillspector.json` | Native SkillSpector report preserved as the primary scanner evidence. |
| `summary.json` | Compact normalized risk, reason, and confidence summary used by downstream consumers. |
| `scanner-config.json` | Effective scanner and LLM configuration used for this scan. |
| `hashes.json` | SHA-256 integrity hashes for the other BOE files. |

## 4. Catalog Builder and Astro Site Build

```mermaid
flowchart LR
  skills[/Skill packages/]
  boe[/Matching BOE/]
  policy[/Exchange policy and site config/]
  catalogBuilder(Catalog builder)
  artifacts[/Static catalog artifacts/]
  astroBuilder(Astro builder)
  site[/Published Astro Exchange Site/]

  skills -->|supplies| catalogBuilder
  boe -->|supplies| catalogBuilder
  policy -->|configures| catalogBuilder
  catalogBuilder -->|materializes| artifacts
  artifacts -->|feeds| astroBuilder
  astroBuilder -->|publishes| site

  subgraph staticCatalogArtifacts[Static catalog artifacts]
    index[/index and detail JSON/]
    tables[/Scanner tables/]
    zips[/Skill ZIPs/]
    runs[/Scanner-run mirrors/]
  end
```

The index, tables, detail records, ZIPs, and scanner-run mirrors are static projections for the present site. They are not durable evidence and are not committed.

## 5. CI Orchestration Paths

```mermaid
flowchart TD
  mr{{Merge request changes skills}}
  review(review:skills)
  reviewerArtifacts[/Reviewer artifacts/]

  skillMerge{{Default-branch skill change}}
  schedule{{Scheduled publication}}
  publish(publish:exchange)
  official[/Official BOE and generated catalog artifacts/]
  boeCommit(Commit durable BOE when configured)

  otherPush{{Default-branch change without skill changes}}
  generate(generate:exchange)

  astroBuilder(Astro builder: pages job)
  deployed[/Published Astro Exchange Site/]

  mr -->|triggers| review
  review -->|produces| reviewerArtifacts
  skillMerge -->|triggers| publish
  schedule -->|triggers| publish
  publish -->|produces| official
  official -->|stages| boeCommit
  official -->|feeds| astroBuilder
  astroBuilder -->|publishes| deployed
  otherPush -->|triggers| generate
  generate -->|supplies| astroBuilder
```

Merge-request assessment is advisory and does not publish official BOE or deploy the Astro Exchange Site. Official publication happens on scheduled pipelines or default-branch skill changes; the Astro builder consumes static catalog artifacts from the publication or generation job.

### Current combined implementation and separation boundary

Both `publish:exchange` and `generate:exchange` invoke the same `build_exchange()` routine. It validates skill metadata, reuses or creates BOE, and materializes static catalog artifacts in one combined orchestration path. `publish:exchange` runs for scheduled publication and skill changes, and may commit durable BOE; `generate:exchange` runs for other default-branch changes and does not commit BOE. If it also committed BOE, each bot-created default-branch commit could trigger another generation job and another bot commit, creating an infinite CI loop.

The underlying functions are already largely separable. A future refactor could use an evidence builder that accepts skill packages, policy, and scan configuration and produces validation outcomes plus BOE bundles; a catalog builder that accepts skill packages, BOE bundles, and site policy and produces indexes, details, tables, ZIPs, and scanner-run projections; and the existing Astro builder that turns those static artifacts into the published site. The significant CI concern is passing newly created BOE to the catalog builder in the same pipeline as a job artifact, rather than waiting for the bot commit to be present in a later checkout. This operational constraint explains the current coupling: one job can create or reuse BOE and immediately materialize catalog artifacts in its own workspace, avoiding a job-to-bot-commit-to-fresh-checkout orchestration sequence. The tradeoff of a split same-pipeline handoff is that publication would build from a transient job artifact rather than source-controlled BOE; it assumes the BOE is committed successfully and that the committed BOE exactly matches the evidence used to materialize the catalog.

```mermaid
flowchart TD
  mr{{Merge request changes skills}}
  review(review:skills)
  reviewerArtifacts[/Reviewer artifacts/]

  skillMerge{{Default-branch skill change}}
  schedule{{Scheduled publication}}
  existingBoe[/Existing tracked BOE/]
  evidenceBuilder(Evidence builder: publish:exchange)
  evidenceResult[/Validation outcomes and official BOE artifact/]
  commitBoe(Commit durable BOE)
  trackedBoe[/Tracked BOE for later pipelines/]

  otherPush{{Default-branch change without skill changes}}
  catalogBuilder(Catalog builder: generate:exchange)
  catalogArtifacts[/Static catalog artifacts/]
  astroBuilder(Astro builder: pages job)
  site[/Published Astro Exchange Site/]

  mr -->|triggers| review
  review -->|produces| reviewerArtifacts
  skillMerge -->|triggers| evidenceBuilder
  schedule -->|triggers| evidenceBuilder
  existingBoe -->|supplies| evidenceBuilder
  evidenceBuilder -->|produces| evidenceResult
  evidenceResult -->|stages| commitBoe
  commitBoe -->|persists| trackedBoe

  otherPush -->|triggers| catalogBuilder
  trackedBoe -->|supplies| catalogBuilder
  evidenceResult -->|supplies| catalogBuilder
  catalogBuilder -->|materializes| catalogArtifacts
  catalogArtifacts -->|feeds| astroBuilder
  astroBuilder -->|publishes| site
```
