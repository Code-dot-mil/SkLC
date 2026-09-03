# Skill Exchange Static Site

This package is a ready-to-deploy Skill Exchange catalog. It includes the built site, downloadable skill packages, and GitLab Pages configuration. Follow this guide to publish the catalog from a GitLab project or see the alternate hosting option at the bottom.

## Deploy the prebuilt static site on GitLab Pages

### 1. Create the GitLab project

1. Sign in to your organization's GitLab website.
2. Select **Create new** in the upper-right corner.
3. Select **New project/repository**.
4. Select **Create blank project**.
5. Enter the project name.
6. Select the group or namespace where the project will be stored.
7. Select the visibility level.
8. Select **Initialize repository with a README**.
9. Select **Create project**.
10. Select **Deploy > Pages** from the project sidebar.
11. Leave **Use unique domain** enabled.

[GitLab help: Create a blank project](https://docs.gitlab.com/user/project/#create-a-blank-project)

### 2. Enable a Linux runner

1. Open the project in GitLab.
2. Select **Settings > CI/CD** from the left sidebar.
3. Expand **Runners**.
4. Find the available Linux group or instance runner.
5. Select **Enable for this project**.
6. Copy the runner tag shown in GitLab.

[GitLab help: Runners](https://docs.gitlab.com/ci/runners/)

[GitLab help: Runner tags](https://docs.gitlab.com/ci/runners/configure_runners/#control-jobs-that-a-runner-can-run)

### 3. Add the runner tag variable

1. Select **Settings > CI/CD** from the project sidebar.
2. Expand **Variables**.
3. Select **Add variable**.
4. Leave **Type** set to **Variable**.
5. Enter `PAGES_RUNNER_TAG` in **Key**.
6. Enter the Linux runner tag in **Value**.
7. Leave **Environment scope** set to **All**.
8. Leave **Mask variable** cleared.
9. Leave **Protect variable** cleared.
10. Select **Add variable**.

[GitLab help: Add a project CI/CD variable](https://docs.gitlab.com/ci/variables/#for-a-project)

[GitLab help: Use a CI/CD variable as a runner tag](https://docs.gitlab.com/ci/runners/configure_runners/#use-cicd-variables-in-tags)

### 4. Add the site to the GitLab project

Install and configure Git, then use the following process:

1. Open the project in GitLab.
2. Select **Code** and copy the repository's HTTPS clone address.
3. Open a terminal in the location where the project will be stored.
4. Identify the folder containing the site package and the project's default branch name.
5. Replace the placeholders in the terminal reference below.
6. Run the commands in order to clone the project, copy the site, create a commit, and push it to GitLab.

#### Terminal reference

Replace each value inside angle brackets with the corresponding value from the GitLab project or computer.

- `<repository-url>`: The HTTPS clone address copied from GitLab.
- `<project-folder>`: The folder created when the repository is cloned.
- `<site-package-folder>`: The folder containing the website files.
- `<commit-message>`: A short description of the deployment.
- `<default-branch>`: The default branch displayed in GitLab.

Run the following commands after replacing the values in angle brackets:

```sh
repository_url="<repository-url>"
project_folder="<project-folder>"
site_package_folder="<site-package-folder>"
commit_message="<commit-message>"
default_branch="<default-branch>"

git clone "$repository_url" "$project_folder"
cp -a "$site_package_folder"/. "$project_folder"/
cd "$project_folder"
git add --all
git commit -m "$commit_message"
git push origin "$default_branch"
```

[GitLab help: Install and configure Git](https://docs.gitlab.com/topics/git/how_to_install_git/)

[GitLab help: Clone a repository](https://docs.gitlab.com/topics/git/clone/)

[GitLab help: Authenticate over HTTPS with a personal access token](https://docs.gitlab.com/user/profile/personal_access_tokens/)

[GitLab help: Stage, commit, and push changes](https://docs.gitlab.com/topics/git/commit/)

### 5. View the deployment pipeline

1. Select **Build > Pipelines** from the project sidebar.
2. Select the newest pipeline for the default branch.
3. Open the job named `pages`.
4. The `pages` job displays **Passed** when the deployment is complete.

[GitLab help: View pipelines](https://docs.gitlab.com/ci/pipelines/#view-pipelines)

[GitLab help: View a job log](https://docs.gitlab.com/ci/jobs/job_logs/#view-job-logs)

### 6. Open the GitLab Pages site

1. Select **Deploy > Pages** from the project sidebar.
2. Select the Pages deployment.
3. Select the published website address.
4. Open a skill from the catalog.
5. Download a skill ZIP from the site.

[GitLab help: GitLab Pages](https://docs.gitlab.com/user/project/pages/)

[GitLab help: Access a Pages site](https://docs.gitlab.com/user/project/pages/#access-to-your-pages-site)

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
