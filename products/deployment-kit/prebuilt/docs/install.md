# Install the prebuilt deployment kit

Download `deployment-kit-prebuilt-<version>.zip` from
[SkLC Releases](https://github.com/Code-dot-mil/SkLC/releases).
You need unzip support and a SHA-256 utility.

## Check the download and unzip

Expand the asset details on the GitHub Release page to see its `sha256:` digest.
Calculate the downloaded ZIP's SHA-256 with one of these commands, replacing
`<version>` with the version in its filename:

On Linux, use:

```sh
sha256sum "deployment-kit-prebuilt-<version>.zip"
```

On macOS, use:

```sh
shasum -a 256 deployment-kit-prebuilt-<version>.zip
```

On Windows (PowerShell), use:

```powershell
Get-FileHash -Algorithm SHA256 "deployment-kit-prebuilt-<version>.zip"
```

Compare the 64-character result with the digest GitHub displays for that same
asset, ignoring letter case and the `sha256:` prefix. If they differ, stop and download it again.
Once they match, unzip it into a new folder:

```sh
unzip deployment-kit-prebuilt-<version>.zip -d deployment-kit-prebuilt-<version>
cd deployment-kit-prebuilt-<version>
```

The ZIP contains `public/`, `docs/`, `README.md`, and `.gitlab-ci.yml` directly.
ZIPs under `public/downloads/` are individual skill downloads served by the site.

## Deploy

For [GitLab Pages](deploy-gitlab-pages.md), copy the complete extracted package,
including hidden files, into the target project. You also need Git configured
with a commit name and email, permission to push to the project, and an available
Linux runner that can pull the configured job image. The included job publishes
`public/` directly.

For [another static host](deploy-static-hosting.md), serve the complete `public/`
directory. Keep its directory structure unchanged so pages, assets, and skill
downloads remain connected. Deployment requires no Python, Node.js, site build,
or assessment tooling.
