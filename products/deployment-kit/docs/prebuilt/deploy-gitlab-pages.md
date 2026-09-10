# Deploy with GitLab Pages

First complete [installation and verification](install.md).

## Prepare GitLab and Git

Create or select an empty [GitLab project](https://docs.gitlab.com/user/project/)
and confirm that the account has permission to push to it. GitLab Pages publishes
the `public/` directory through the included `.gitlab-ci.yml`; see the
[GitLab Pages documentation](https://docs.gitlab.com/user/project/pages/) for
instance-specific availability and URLs.

GitLab runners execute CI jobs. In the project, open **Settings > CI/CD >
Runners** and select an available Linux runner with a Docker or Kubernetes
executor that supports job images. Runner tags control which jobs a runner can
accept; the job's image selects its container environment. See the GitLab documentation for
[runners](https://docs.gitlab.com/ci/runners/),
[runner scope](https://docs.gitlab.com/ci/runners/runners_scope/), and
[runner setup](https://docs.gitlab.com/user/get_started/get_started_runner/).
The shipped job selects the official `python:3.12-slim` image, which provides a
POSIX shell and Python for verification without installing additional packages.
Python is needed only for the pre-deployment check, not to serve the website.
The runner must be allowed to pull the selected image; Python does not need to
be installed on the runner host.

If you are unsure which runner tags are available, ask your GitLab
administrator.

In **Settings > CI/CD > Variables**, create `PAGES_RUNNER_TAG` with the tag of the
selected runner. GitLab documents project and group variables in
[CI/CD variables](https://docs.gitlab.com/ci/variables/).

If your environment requires an internal registry, override `PYTHON_IMAGE` with
the complete approved image reference, or override `PYTHON_IMAGE_REGISTRY`,
`PYTHON_IMAGE_REPOSITORY`, and `PYTHON_IMAGE_TAG`. The image must include a POSIX
shell and `python3` running Python 3.12 or newer. Set these as project or group
CI/CD variables instead of editing the checksummed package files. See GitLab's
[job image configuration](https://docs.gitlab.com/ci/yaml/#image).

The following Git configuration is a template. Replace `<git-user-name>` with
the name to record on commits and `<git-user-email>` with the corresponding
email:

```sh
git config --global user.name "<git-user-name>"
git config --global user.email "<git-user-email>"
```

## Add the release to the project

The following commands are a template. Replace `<gitlab-project-url>` with the
SSH or HTTPS clone URL from the GitLab project's **Code** menu, and replace
`<local-project-directory>` with the directory where the repository should be
cloned. Choose a location outside the extracted release directory, then run the
commands from the extracted release root.

```sh
git clone "<gitlab-project-url>" "<local-project-directory>"
cp -a . "<local-project-directory>/"
cd "<local-project-directory>"
git add -A
git commit -m "Deploy SkLC prebuilt site"
git branch -M main
git push origin main
```

## Verify the deployment

Open **Build > Pipelines** and select the pipeline created by the push. The
`pages` job verifies the release manifest and checksums before publishing the
existing `public/` directory. After it passes, open **Deploy > Pages**, follow
the published URL, and confirm that the catalog loads with styling, a skill detail
page opens, and a skill download works. The runner does not build the site or
rewrite its links.
