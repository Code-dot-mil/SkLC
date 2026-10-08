# Release manifest

`release-manifest/v1/` contains the schema used by the prebuilt package builder and shipped verifier. The package vendors this schema so it can be verified offline.

The manifest records the product version, source revision, supported contracts, and artifact checksums. Its own checksum is recorded separately in `SHA256SUMS.txt`.
