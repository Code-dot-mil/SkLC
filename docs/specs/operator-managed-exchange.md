# Operator-Managed Exchange Spec

## Decision baseline

This spec follows `docs/decisions.md`: the deployment kit remains a standalone GitHub release consumed in GitLab, and product updates must not collapse product boundaries.

## Milestone

`docs/roadmap.md` section 3.8, Post-Q3 - Operator-managed skill exchange.

## Status

Draft.

An agent must not execute this spec until a human reviewer changes this status
to Approved.

## Outcome

An operator adds locally owned skills, BOE, and catalog policy, then applies supported updates without modifying that local content.

## Release artifact

GitHub Releases publish one archive named
`deployment-kit-operator-<version>.tar.gz`, plus external
`release-manifest.json` and `SHA256SUMS.txt` assets. After extraction, the archive
root is named `deployment-kit-operator-<version>/` and contains the installed
tree shown below plus internal copies of `release-manifest.json` and
`SHA256SUMS.txt`.

The external release manifest is authoritative before extraction. The internal
manifest must be byte-for-byte identical to the external manifest after
extraction. The external `SHA256SUMS.txt` records the archive, external manifest,
and every downloadable release asset. The internal `SHA256SUMS.txt` records the
installed tree files inside the archive.

This is the first operator-managed baseline release. It builds on the operator
foundation release but starts a new managed-update proof using
`<managed-baseline-version>` and `<managed-candidate-version>`.

The operator-managed baseline release contains:

- Compatible released catalog content.
- Reference site source and build tooling.
- Assessment kit and dependencies.
- Reference GitLab CI.
- Operator command-line tooling and documentation.
- Empty `local/` subtree owned by the operator.
- Release manifest, applied-version record schema, and checksums.

The installed GitLab project has this tree:

```text
.gitlab-ci.yml                    Released root GitLab CI entrypoint; replaced by full updates
release-manifest.json             Internal copy of the external release manifest; replaced by full updates
SHA256SUMS.txt                        Internal installed-tree checksums; replaced by full updates
catalog/                         Released catalog content; replaced by full or catalog-only updates
  skills/
  boe/
site/                            Released site source and build tooling; replaced by full updates
wheels/                          Released assessment kit and dependencies; replaced by full updates
ci/                              Released reference GitLab CI; replaced by full updates
docs/                            Released operator documentation; replaced by full updates
contracts/                       Vendored contracts consumed by this release; replaced by full updates
  operator-applied/v1/
operator/
  bin/skill-exchange-operator    Install, verify, build, and update command

.operator/
  applied-version.json           Record for the installed release
  staging/                       Temporary update extraction and verification workspace
  rollback/                      Temporary rollback workspace used during replacement

local/                           Operator-owned; never replaced by product updates
  skills/
  boe/
  catalog-policy.yaml
```

The release artifact must not contain non-empty operator content under `local/`.
It may create missing empty `local/skills/` and `local/boe/` directories during
install. On update, the artifact's `local/` tree is ignored after structure
validation.

## Ownership boundary

Delivered product content lives outside `local/`. The operator owns:

- `local/skills/`
- `local/boe/`
- `local/catalog-policy.yaml`

Supported updates must preserve `local/` unchanged.

Released-owned paths are `.gitlab-ci.yml`, `release-manifest.json`,
`SHA256SUMS.txt`, `catalog/`, `site/`, `wheels/`, `ci/`, `docs/`, `contracts/`, and
`operator/`. The update command must verify that those paths match
`.operator/applied-version.json` before replacement. If an operator edits
released-owned paths directly, the update fails closed and reports the drift
instead of overwriting it. Supported customization is limited to `local/`.

## Catalog and BOE precedence

The site build discovers skill packages from `catalog/skills/` and
`local/skills/`. Skill identity is the path-derived skill name from the
skill-package contract. Duplicate skill names across released and local skills
are a validation error; local skills do not shadow released skills.

Catalog policy precedence is explicit:

1. If `local/catalog-policy.yaml` exists, it is the effective publication policy for
   both released and local skills.
2. If `local/catalog-policy.yaml` is absent, every valid released catalog skill
   is published and local skills are not published.
3. If the effective policy is present but invalid, the build fails closed and
   must not fall back to default publication.

BOE precedence is per skill name:

1. If `local/boe/<skill-name>/boe.json` exists, it is the effective BOE for that
   skill.
2. Otherwise, if `catalog/boe/<skill-name>/boe.json` exists, the released BOE is
   the effective BOE.
3. If the effective BOE exists but fails BOE verification, the build fails
   closed.
4. Missing BOE does not change publication; local catalog policy controls
   publication when present. Otherwise, the default released-skill publication
   rule applies.

The build must reject absolute paths, parent-directory traversal, and symbolic
links that escape the skill or BOE trees.

## Operator commands

The release provides `operator/bin/skill-exchange-operator` with these commands:

- `install --release-archive <path> --manifest <path> --checksums <path>
  --target <path>` installs a verified full release into an empty target or a
  target containing only an empty `local/` subtree.
- `verify --target <path>` validates the installed tree, the applied-version
  record, checksums for released-owned paths, the effective catalog selection,
  discovered skills, and effective BOE.
- `materialize --target <path>` runs `verify` and generates site data from the
  effective released-plus-local catalog inputs.
- `build-site --target <path>` builds the static site from generated site data.
- `update --release-archive <path> --manifest <path> --checksums <path>
  --target <path>` applies a verified full release update.
- `update-catalog --catalog-archive <path> --catalog-sha256 <sha256>
  --target <path>` applies a verified catalog-only update.

`update` supports full operator-release updates. `update-catalog` supports
catalog-only updates using a compatible skill catalog release. The operator must
reject artifacts that attempt to update only the assessment kit, only the site,
or an arbitrary custom site.

## Update process

`update` performs these gates before replacing any released-owned path:

1. Read `.operator/applied-version.json` and verify its schema.
2. Verify every installed released-owned file against the checksums recorded for
   the applied release. Ignore `local/` for this drift check.
3. Verify the external candidate `SHA256SUMS.txt` records both the external
   candidate release manifest and candidate release archive.
4. Verify the external candidate release manifest digest and archive digest
   against external `SHA256SUMS.txt`.
5. Verify the external candidate release manifest against
   `skill-exchange-release-manifest/v1` and confirm its `artifacts[]` records
   the same archive digest verified by `SHA256SUMS.txt`.
6. Extract the candidate release into `.operator/staging/<version>/` and verify
   that all extracted paths are relative, stay within staging, and contain no
   symbolic links that escape staging.
7. Verify the candidate tree contains exactly the required released-owned files
   and roots, the empty `local/` structure, internal `release-manifest.json`,
   and internal checksums. The internal manifest must match the external
   manifest byte-for-byte.
8. Verify every candidate released-owned file against the internal candidate
   checksums.
9. Verify declared contract major versions and product compatibility. Unsupported
   major versions fail closed.
10. Validate the combined released-plus-local catalog using the precedence rules
   above.
11. Produce a replacement plan that removes and replaces only released-owned
    paths and `.operator/applied-version.json`.

Only after every gate succeeds may `update` move existing released-owned paths to
`.operator/rollback/<previous-version>/`, move the staged released-owned paths
into place, write the new applied-version record, and remove rollback state.
`local/` is never moved, copied, deleted, or edited.

`update-catalog` performs the same checksum, manifest, extraction-safety,
contract-version, and combined catalog validation gates for the candidate skill
catalog release. Only after every gate succeeds may it replace `catalog/` and
update `.operator/applied-version.json` with the new catalog version and
catalog file checksums. It must not modify `local/` or released-owned roots
outside `catalog/`.

## Applied-version record

`.operator/applied-version.json` records the installed release and the checksums
that future verification and update commands use. It validates against
`contracts/operator-applied/v1/applied-version.schema.json`, which is vendored
in the release. It uses this schema:

```json
{
  "schema_version": "skill-exchange-operator-applied/v1",
  "release_version": "<managed-candidate-version>",
  "applied_at": "2026-01-31T12:34:56Z",
  "release_manifest_sha256": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "release_archive_sha256": "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "products": {
    "deployment_kit": "<managed-candidate-version>",
    "catalog": "<compatible-catalog-version>",
    "assessment_kit": "<compatible-assessment-kit-version>"
  },
  "contracts": {
    "release_manifest": "v1",
    "catalog_policy": "v1",
    "skill_package": "v1",
    "boe": "v1"
  },
  "released_roots": [
    "catalog",
    "site",
    "wheels",
    ".gitlab-ci.yml",
    "release-manifest.json",
    "SHA256SUMS.txt",
    "ci",
    "docs",
    "contracts",
    "operator"
  ],
  "local_root": "local",
  "files": [
    {
      "path": "catalog/skills/python-secure-code-review/SKILL.md",
      "sha256": "sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
    }
  ],
  "previous_release_version": "<managed-baseline-version>"
}
```

`files[*].path` values are relative paths under released-owned roots. They must
not be absolute, contain parent-directory traversal, or point into `local/`.

## Rollback and no-change guarantees

Failed verification leaves the installed release, applied-version record, and
`local/` byte-for-byte unchanged. The command may leave ignored staging
diagnostics under `.operator/staging/`.

Failed replacement must restore all released-owned paths and the previous
applied-version record from `.operator/rollback/` before exiting nonzero. A
successful update is observable only when `verify --target <path>` passes and
`.operator/applied-version.json` records the candidate release.

## Contracts

The release consumes compatible catalog, assessment-kit, BOE, catalog-policy, skill-package, and release-manifest contracts by declared version.

The operator-managed milestone does not define a new assessor-output contract.
The installed assessment kit declares supported native assessor report versions;
obsolete assessor output is rejected by BOE verification.

## GitLab proof

The installed `.gitlab-ci.yml` defines these stages in order:

```yaml
stages:
  - verify
  - site_data
  - site_build
  - deploy
```

The minimum job contract is:

| Job | Stage | Required behavior |
|---|---|---|
| `operator_verify` | `verify` | Runs `operator/bin/skill-exchange-operator verify --target .` and fails before build on invalid released or local content. |
| `operator_build` | `site_data` | Runs `operator/bin/skill-exchange-operator materialize --target .` and produces generated site inputs. |
| `operator_site` | `site_build` | Runs `operator/bin/skill-exchange-operator build-site --target .` and builds `public/` from released site source and generated inputs. |
| `pages` | `deploy` | Publishes top-level `public` as the GitLab Pages artifact. |

The CI must not run update commands automatically. Updates are explicit
operator actions followed by the same verify, build, and deploy pipeline.

Acceptance requires a clean GitLab project that:

1. Receives the operator release from GitHub Releases and verifies checksums.
2. Installs the operator release.
3. Adds local skill, BOE, and catalog policy content.
4. Builds and deploys to GitLab Pages.
5. Applies a staged full update.
6. Applies a staged catalog-only update.
7. Verifies checksums before replacement.
8. Preserves `local/` unchanged.
9. Leaves the installed release unchanged after failed verification.

The minimum automated test scenario is:

1. Install operator release `<managed-baseline-version>` in a clean GitLab project and run
   `operator/bin/skill-exchange-operator verify --target <project>`.
2. Add `local/skills/local-example/SKILL.md`, matching
   `local/boe/local-example/boe.json`, and `local/catalog-policy.yaml` using
   `include-list` for one released skill and `local-example`.
3. Run `materialize --target <project>` and `build-site --target <project>`,
   then deploy the GitLab Pages artifact.
4. Record SHA-256 hashes for every file under `local/`.
5. Run `update --release-archive <managed-candidate-version-archive>
   --manifest <managed-candidate-version-manifest>
   --checksums <managed-candidate-version-checksums> --target <project>`.
6. Run `verify --target <project>` and confirm the applied-version record now
   names `<managed-candidate-version>`.
7. Confirm every recorded `local/` hash is unchanged and the local skill remains
   published by the effective policy.
8. Run `update-catalog --catalog-archive <catalog-candidate-archive>
   --catalog-sha256 <catalog-candidate-sha256> --target <project>`.
9. Run `verify --target <project>` and confirm the applied-version record names
   the new catalog version, every recorded `local/` hash is unchanged, and
   released-owned roots outside `catalog/` are unchanged.
10. Repeat the update with a corrupted candidate archive or checksum and confirm
   the command exits nonzero, the applied-version record still names
   `<managed-candidate-version>`, released-owned hashes are unchanged, and all
   `local/` hashes are unchanged.

## Exclusions

- Compatibility guarantees for arbitrary custom sites.
- Offline or air-gapped operation.
- Historical skill serving.
- Compatibility with obsolete assessor-output formats.
- Assessment-kit-only and site-only partial updates.
