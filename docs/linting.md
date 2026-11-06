# Local lint checks

Install Python and Node development dependencies from the repository root:

```sh
uv sync --extra test --group lint
npm ci
npm ci --prefix products/deployment-kit/operator/site
```

Install `actionlint` and `shellcheck` with your system package manager. On macOS:

```sh
brew install actionlint shellcheck
```

The npm lockfiles pin ESLint, typescript-eslint, React Hooks and Astro plugins, Astro checking, markdownlint-cli2, and Prettier. The Python lockfile pins gitlab-ci-verify-bin, which bundles its own ShellCheck.

| Command | Scope |
| --- | --- |
| `just python-lint` | Python implementation, tooling, and tests through Ruff |
| `just site-typecheck` | Existing TypeScript compiler check |
| `just site-code-lint` | JavaScript, TypeScript, React Hooks, and Astro syntax through ESLint |
| `just site-astro-check` | Astro and TypeScript diagnostics through `astro check` |
| `just markdown-lint` | Markdown structure, including agent and bundled skills |
| `just markdown-check` | Markdown formatting through Prettier |
| `just github-lint` | GitHub Actions configuration and embedded ShellCheck diagnostics |
| `just gitlab-lint` | GitLab template scripts through the verifier's bundled ShellCheck |

`just lint` runs these checks and stops on failure. Run individual commands to collect the full baseline when multiple checks fail. GitHub CI runs each check on pull requests and pushes to `main`, with independent results for Python, GitLab scripts, TypeScript, ESLint, Astro, Markdown structure, Markdown formatting, and workflow lint. The final site artifact requires all check jobs to succeed.

CI installs the locked npm dependencies and GitLab verifier, and downloads actionlint 1.7.12 with SHA-256 verification. The workflow job checks that the Ubuntu runner's ShellCheck is available before invoking actionlint, so shell analysis cannot be silently omitted. These checks run on GitHub-hosted runners and require no provider credentials.

Prettier uses one source line per prose paragraph (`proseWrap: "never"`), relying on editor soft wrapping. Markdownlint's line-length rule is disabled to match. Code examples are not reformatted. To apply Markdown formatting deliberately, run `npm run markdown:format`; formatting catalog skill content changes assessment hashes and requires refreshed assessments.

GitLab templates are checked without the remote lint API. The Operator pipeline is staged with its included assessment template in the consumer's directory layout. To validate pipeline semantics, also use GitLab's CI Lint API in a consuming project's context. Local script checks do not prove pipeline validity, resolve project variables, or simulate pipeline creation.

The four catalog `SKILL.md` files are temporarily excluded from Prettier in `.prettierignore` until their assessments can be refreshed. Markdownlint still checks them. The current catalog files and assessment pairs remain unchanged.
