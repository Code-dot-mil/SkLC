# Deploy the prebuilt static site

## 1. Extract the site

Extract the provided static-site ZIP to a local directory.

## 2. Prepare GitLab

1. Create an empty GitLab project.
2. Use an available Linux GitLab runner for the project.
3. In **Settings > CI/CD > Variables**, add `PAGES_RUNNER_TAG` with the exact tag assigned to that runner.
4. Allow the runner and variable to run on protected branches if `main` is protected.

## 3. Upload the extracted site

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

## 4. Run the pipeline

1. Open **Build > Pipelines** in the GitLab project.
2. Confirm the pipeline for `main` starts automatically.
3. Wait for the `pages` job to pass.

## 5. Verify the deployment

1. Open **Deploy > Pages** in the GitLab project.
2. Open the published Pages URL.
3. Confirm the catalog loads and a skill ZIP can be downloaded.
