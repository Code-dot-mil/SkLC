# Product Release Manifest Contract v1

A release manifest describes the installable files inside one extracted product
archive. It does not describe the containing archive and must never include the
archive's digest; doing so would make an internal manifest self-referential.

`artifacts[]` records every regular file beneath the extracted archive root
except `release-manifest.json` and `SHA256SUMS.txt`. Each path is relative to the
archive root and each digest covers the exact installed file bytes. Symbolic
links, absolute paths, parent traversal, duplicate paths, missing files, digest
mismatches, and unrecorded installed files fail verification.

The archive's internal `SHA256SUMS.txt` contains the same file set and digests as
`artifacts[]`, with the `sha256:` prefix removed and conventional two-space
separation between digest and path. This lets a customer run `sha256sum -c
SHA256SUMS.txt` after extraction and independently compare the result with the
manifest.

When a product release exposes a manifest before extraction, that external
manifest is a byte-for-byte copy of the internal `release-manifest.json`. Its
product-qualified filename is `<product>-<version>.release-manifest.json` so a
cumulative GitHub Release can attach sidecars for more than one standalone
product. An external `<product>-<version>.SHA256SUMS.txt` records the product
archive and external manifest. It has a different scope from the internal
checksum file and therefore is not copied into the archive.

This two-layer verification avoids a circular archive digest:

1. Verify the archive and external manifest with the external checksum file.
2. Extract the archive.
3. Confirm the internal and external manifests are byte-for-byte identical.
4. Verify installed files with the internal checksum file and compare its file
   set and digests with `artifacts[]`.

The release manifest's `produces` and `consumes` fields declare serialized
contract identifiers used by the product. They do not create runtime imports
from another product or from the maintainer repository's `contracts/` tree.
