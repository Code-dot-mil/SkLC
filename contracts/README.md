# Product Contracts

This directory contains the versioned, serialized contracts exchanged between independently releasable Skill Exchange products. It is a source-governance boundary, not a runtime package or an additional product.

A contract belongs here only when at least two independently releasable products must agree on its representation. Product releases vendor the exact contract schemas they produce or consume; products do not import executable code from this directory.

## Contracts and ownership

| Contract | Governing product | Consumers |
| --- | --- | --- |
| Skill package | Assessment kit | Assessment kit, catalog tooling |
| Assessment result | Assessment kit | BOE writer, review tooling |
| BOE | Assessment kit | Catalog tooling |
| Assessment artifacts | Assessment kit | GitLab CI profile, operator tooling |
| Catalog manifest | Skill catalog | Deployment kit, custom exchanges |
| Catalog policy | Skill catalog | Maintainer and operator catalog publication |
| Product release manifest | Maintainer release tooling | Product installers, update tooling, operators |

The governing product owns a contract's meaning and change process. A neutral source location does not transfer that ownership. Policy schemas are owned by the component that evaluates them; individual policy files are owned by the publisher or operator applying them.

## Versioning

- Contract identifiers include a major version, such as `skill-exchange-boe/v1`.
- Additive optional fields may be introduced within a major version when readers tolerate them.
- Removing a field, changing its meaning, or adding a required field requires a new major version.
- Readers reject unsupported major versions rather than silently interpreting them.
- Product release manifests declare the contract versions they produce and consume.
- Product release manifests also identify the source revision and checksums for released artifacts. They do not include their own checksum in the artifact list.
- Contract examples explain the intended shape but are not substitutes for the schemas and contract prose.

## Current-catalog BOE policy

Current catalog materialization supports only the current BOE major version. When the BOE contract has a breaking update, currently served skill versions are reassessed with the latest assessment kit.

Legacy BOE may remain as historical evidence. Its presence is not an error, but it is not eligible for a current assessed catalog. A currently served skill without matching BOE in the supported schema is missing current evidence and must be reassessed or excluded. Serving historical skill versions with historical BOE would require an explicitly versioned historical catalog and compatible tooling; it is not implicit backward compatibility.

## Scope constraints

This directory contains no executable implementation code, deployment-specific configuration, policy instances, CI definitions, or product packaging logic. Shared implementation belongs in a product; shared serialized boundaries belong here.
