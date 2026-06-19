# Skill Exchange CI

The repository owns its GitLab CI directly in `.gitlab-ci.yml`. It does not import external CI components.

## Pipeline Shape

- `lint`, `test`, and `audit` run for merge requests and default-branch pushes when site code, exchange tooling, tests, or CI configuration changes.
- `review:skills` runs only for merge requests that change `skills/**/*`. It validates changed skill packages, runs SkillSpector, writes reviewer artifacts, and can post a merge request comment when comment variables are configured.
- `publish:exchange` runs only for scheduled pipelines. It generates official exchange evidence under `.exchange/generated/` and can commit those generated files back when bot push variables are configured.
- `pages` runs on default-branch push pipelines and publishes the built static site as GitLab Pages artifacts.
- By default, `pages` uses the runner tag in `PAGES_RUNNER_TAG`. For MITRE GitLab Pages this defaults to `pages-no-cui`.

## Required Schedule

Create a GitLab pipeline schedule for the default branch using the cadence required by the target environment, such as nightly. The schedule should run with `CI_PIPELINE_SOURCE=schedule`, which triggers `publish:exchange`.

For official BOE publication, run the schedule as the exchange bot or provide bot credentials through masked CI variables.

## Configurable Variables

All environment-specific values are CI variables:

- `PYTHON_IMAGE_REGISTRY`, `PYTHON_IMAGE_REPOSITORY`, `PYTHON_IMAGE_TAG`, and `PYTHON_IMAGE` select the Python runner image.
- `NODE_IMAGE_REGISTRY`, `NODE_IMAGE_REPOSITORY`, `NODE_IMAGE_TAG`, and `NODE_IMAGE` select the Node runner image.
- `PAGES_RUNNER_TAG` selects the GitLab Pages runner tag.
- `SKILLSPECTOR_INSTALL_COMMAND` installs SkillSpector when the runner image does not already include it.
- `SKILLSPECTOR_BIN` points to a SkillSpector binary when it is not on `PATH`.
- `SKILL_EXCHANGE_REVIEW_SCAN_MODE` controls MR review scanning: `static-only` or `llm-assisted`.
- `SKILL_EXCHANGE_PUBLISH_SCAN_MODES` controls scheduled publication scanning, using comma or space separated modes.
- `SKILL_EXCHANGE_LLM_API_KEY`, `SKILL_EXCHANGE_LLM_BASE_URL`, `SKILL_EXCHANGE_LLM_MODEL`, and `SKILL_EXCHANGE_LLM_PROVIDER` configure LLM-assisted scans without tying the repository to a specific provider.
- `SKILL_EXCHANGE_POST_REVIEW_COMMENT`, `SKILL_EXCHANGE_REVIEW_TOKEN_VARIABLE`, and `SKILL_EXCHANGE_REVIEW_TOKEN_HEADER` control optional merge request comments.
- `EXCHANGE_PUBLISH_COMMIT`, `EXCHANGE_PUBLISH_PUSH`, `EXCHANGE_PUBLISH_BRANCH`, `EXCHANGE_PUBLISH_PUSH_URL`, `EXCHANGE_PUBLISH_TOKEN`, and `EXCHANGE_PUBLISH_USERNAME` control generated-output commits.
- `EXCHANGE_BOT_GIT_NAME`, `EXCHANGE_BOT_GIT_EMAIL`, and `EXCHANGE_PUBLISH_COMMIT_MESSAGE` control generated commit metadata.
- Provider credentials and endpoints for LLM-assisted SkillSpector scans should be configured as masked CI variables, not committed to the repository.
