# Skill Exchange Static Site

This package is a ready-to-deploy Skill Exchange catalog. It includes the built site, downloadable skill packages, and GitLab Pages configuration. Follow this guide to publish the catalog from a GitLab project or see the alternate hosting option at the bottom.

## Deploy the prebuilt static site on GitLab Pages

### 1. Extract the site

Extract the provided static-site ZIP to a local directory.

### 2. Prepare GitLab

1. Create an empty GitLab project.
2. Use an available Linux GitLab runner for the project.
3. In **Settings > CI/CD > Variables**, add `PAGES_RUNNER_TAG` with the exact tag assigned to that runner.
4. In **Deploy > Pages**, keep **Use unique domain** enabled. This is the default for new projects on current GitLab versions. The prebuilt site uses root-absolute asset URLs, so it requires a unique Pages domain or a configured custom domain.
5. Allow the runner and variable to run on protected branches if `main` is protected.

### 3. Upload the extracted site

Run these commands in terminal:

```sh
artifact_dir="/path/to/extracted/static-site"
repo_dir="/path/to/sklc-customer-site"
repository_url="git@gitlab.example.org:group/sklc-customer-site.git"

git clone "$repository_url" "$repo_dir"
cp -a "$artifact_dir"/. "$repo_dir"/
cd "$repo_dir"

git add -A
git commit -m "Deploy prebuilt SkLC site"
git branch -M main
git push -u origin main
```

### 4. Run the pipeline

1. Open **Build > Pipelines** in the GitLab project.
2. Confirm the pipeline for `main` starts automatically.
3. Wait for the `pages` job to pass.

### 5. Verify the deployment

1. Open **Deploy > Pages** in the GitLab project.
2. Open the published Pages URL.
3. Confirm the catalog loads, styling is present, filtering works, and a skill ZIP can be downloaded.

## Alternate Hosting Option

As an alternative to using GitLab Pages, you can host this package with a
static web server such as NGINX or Apache HTTP Server, or an object-storage
website service like a Google Cloud Storage bucket configured to host a website.

Copy these site files to the folder or bucket your service publishes to the web,
without changing their folder structure:

- `index.html`
- `_astro/`
- `skills/`
- `downloads/`

The included `README.md` and `.gitlab-ci.yml` are not needed for alternate
hosting. Make the files available at the site's main web address, rather than
inside a subfolder. Then confirm that the catalog and downloads work.
