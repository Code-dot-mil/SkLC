# Install the prebuilt deployment kit

Choose a hosting path before continuing:

- [GitLab Pages](deploy-gitlab-pages.md), using the included deployment job.
- [Another static host](deploy-static-hosting.md), serving the included `public/` directory.

Both paths require an archive extractor and Python 3.12 or newer for offline
verification. No Python packages, Node.js, site build, or assessment tools are
needed. Use a release obtained from the trusted project; these checks detect
inconsistent or damaged files, not an attacker replacing the entire release.

The GitLab path also requires local Git configured with a commit name and email,
and permission to push to the destination project. See the
[Git user manual](https://git-scm.com/docs/user-manual) and
[first-time Git setup](https://git-scm.com/book/en/v2/Getting-Started-First-Time-Git-Setup).

## Extract the archive

Download `deployment-kit-prebuilt-<version>.tar.gz` from GitHub Releases. Open a
POSIX-compatible terminal in the folder containing that download.

The following block is a **template**: replace `<version>` in the assignment with
the exact version in the downloaded filename, without a leading `v`. Keep this
terminal open for the verification step.

```sh
version="<version>"
tar -xzf "deployment-kit-prebuilt-${version}.tar.gz"
cd "deployment-kit-prebuilt-${version}"
```

The extracted directory name must match the version in the archive filename.

## Verify before deployment

Run this command unchanged from the extracted package root. This is the same
verification command used by the included GitLab deployment job:

```sh
python3 -I -S scripts/verify_prebuilt.py .
```

The script validates the manifest against the vendored schema, compares its file
list and digests with `SHA256SUMS.txt`, hashes the package files, and checks the
required layout and static download references. It rejects missing or extra
package files, directory links, unsafe paths, invalid timestamps, and missing
referenced downloads. A top-level `.git` entry is ignored so the same verification
works inside a customer Git checkout. `-I -S` keeps verification independent of
local Python environment settings and installed third-party packages.

In the same terminal, also confirm that the manifest matches the archive version
selected above:

```sh
python3 -I -S scripts/verify_prebuilt.py . --expected-version "$version"
```

A successful check prints `Prebuilt package verified: manifest, checksums, files,
and downloads are valid.` and exits with status zero. If a check fails, stop;
do not edit the metadata to bypass it. Obtain a fresh trusted release or report
the failure to its maintainer.

## Deploy the verified files

For GitLab Pages, follow [Deploy with GitLab Pages](deploy-gitlab-pages.md) and copy
the complete extracted package, including hidden files, into the project. Keep
the file contents unchanged; its local directory name need not match the archive.
The selected Linux runner must already provide Python 3.12 or newer.

For another host, follow [Deploy to another static host](deploy-static-hosting.md)
and serve the complete `public/` directory unchanged.
