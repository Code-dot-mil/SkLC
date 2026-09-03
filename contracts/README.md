# Product Contracts

This directory contains versioned serialized contracts exchanged between
independently releasable Skill Exchange products. It is a source-governance
boundary, not a runtime package or an additional product.

A contract belongs here only when at least two independently releasable products
must agree on its representation. Product releases vendor the exact schemas they
produce or consume; products do not import executable code from this directory.

## Contracts and ownership

| Contract | Governing product | Consumers |
| --- | --- | --- |
| Skill package | Assessment kit | Assessment kit, catalog tooling |
| BOE manifest | Assessment kit | Catalog tooling |
| Assessment artifacts | Assessment kit | GitLab CI profile, operator tooling |
| Catalog policy | Skill catalog | Maintainer and operator catalog publication |
| Product release manifest | Maintainer release tooling | Product installers, update tooling, operators |

The governing product owns a contract's meaning and change process. A neutral
source location does not transfer ownership. Policy schemas are owned by the
component that evaluates them; individual policy files are owned by the
publisher or operator applying them.

## Versioning

The v1 schemas currently in this repository are unreleased working drafts. They
may be corrected before the first product release establishes a published
compatibility promise.

- Contract identifiers include a major version, such as skill-exchange-boe/v1.
- Additive optional fields may be introduced within a major version when readers
  tolerate them.
- Removing a field, changing its meaning, or adding a required field requires a
  new major version after release.
- Readers reject unsupported major versions rather than silently interpreting
  them.
- Product release manifests identify a release version and checksums for its
  artifacts. They do not include their own checksum in the artifact list.
- Contract examples explain intended shape but do not substitute for schemas and
  contract prose.

## BOE handling

A BOE manifest lists native assessor reports that the current software can read.
The hash beside each path binds the manifest to exact assessment bytes. SkLC does
not define a replacement contract for assessor-native output; the released
assessment kit declares the assessor versions it supports. A missing or
unreadable BOE manifest does not change publication in P0; governance decides
whether a skill is published and catalog policy implements that decision.

Assessment artifacts define the retained advice and assessment output trees.
They wrap assessor-native report bytes and BOE manifests in stable filesystem
locations so CI profiles and operator tooling can consume them without knowing
assessment-kit internals.

## Scope constraints

This directory contains no executable implementation code, deployment-specific
configuration, policy instances, CI definitions, or product packaging logic.
Shared implementation belongs in a product; shared serialized boundaries belong
here.
