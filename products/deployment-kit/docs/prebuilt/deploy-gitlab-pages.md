# Deploy with GitLab Pages

## Prepare GitLab and Git

Create or select an empty [GitLab project](https://docs.gitlab.com/user/project/)
and confirm that the account has permission to push to it. GitLab Pages publishes
the `public/` directory through the included `.gitlab-ci.yml`; see the
[GitLab Pages documentation](https://docs.gitlab.com/user/project/pages/) for
instance-specific availability and URLs.

GitLab runners execute CI jobs. In the project, open **Settings > CI/CD >
Runners** and select an available Linux runner. Runner tags control which jobs a
runner can accept. See the GitLab documentation for
[runners](https://docs.gitlab.com/ci/runners/),
[runner scope](https://docs.gitlab.com/ci/runners/runners_scope/), and
[runner setup](https://docs.gitlab.com/user/get_started/get_started_runner/).
The selected runner must provide a POSIX shell and Python 3 so the shipped job
can verify the package without downloading tools.

In **Settings > CI/CD > Variables**, create `PAGES_RUNNER_TAG` with the tag of the
selected runner. GitLab documents project and group variables in
[CI/CD variables](https://docs.gitlab.com/ci/variables/).

The following Git configuration is a template. Replace `Your Name` with the name
to record on commits and `your-email@example.com` with the corresponding email:

```sh
git config --global user.name "Your Name"
git config --global user.email "your-email@example.com"
```

## Add the release to the project

The following commands are a template. Replace `<gitlab-project-url>` with the
SSH or HTTPS clone URL from the GitLab project's **Code** menu, and replace
`<local-project-directory>` with the directory where the repository should be
cloned. Run the commands from the extracted release root.

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
the published URL, and confirm that the catalog loads and a skill download works.
