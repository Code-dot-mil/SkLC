export UV_CACHE_DIR := ".uv-cache"

default:
    just --list

generate:
    uv run python -m skill_exchange.cli generate \
        --skills products/skill-catalog --evidence products/skill-catalog-assessments \
        --generated products/deployment-kit/operator/.exchange/generated

python-lint:
    uv run --extra test ruff check maintainer products

python-lint-fix:
    uv run --extra test ruff check --fix maintainer products

python-test:
    uv run --extra test pytest

site-typecheck:
    npm --prefix products/deployment-kit/operator/site run lint

site-code-lint:
    npm --prefix products/deployment-kit/operator/site run lint:code

site-astro-check:
    npm --prefix products/deployment-kit/operator/site run typecheck:astro

site-lint: site-typecheck site-code-lint site-astro-check

markdown-lint:
    npm run markdown:lint

markdown-check:
    npm run markdown:check

github-lint:
    actionlint

# Local script checks only; GitLab API validation needs a consuming project.
gitlab-lint:
    #!/usr/bin/env bash
    set -euo pipefail
    staging=$(mktemp -d)
    trap 'rm -rf "$staging"' EXIT
    mkdir -p "$staging/operator/ci"
    cp products/deployment-kit/operator/ci/gitlab/.gitlab-ci.yml "$staging/operator/"
    cp products/deployment-kit/operator/ci/gitlab/assessment.yml "$staging/operator/ci/"
    result=0
    for config in \
        products/assessment-kit/ci/gitlab/profile.yml \
        products/deployment-kit/operator/ci/gitlab/assessment.yml \
        products/deployment-kit/prebuilt/ci/gitlab/.gitlab-ci.yml; do
        uv run --group lint gitlab-ci-verify --no-lint-api --gitlab-ci-file "$config" || result=$?
    done
    uv run --project "$PWD" --directory "$staging/operator" --group lint \
        gitlab-ci-verify --no-lint-api --gitlab-ci-file .gitlab-ci.yml || result=$?
    exit "$result"

site-test:
    npm --prefix products/deployment-kit/operator/site run test

site-build:
    npm --prefix products/deployment-kit/operator/site run build

lint: python-lint site-lint markdown-lint markdown-check github-lint gitlab-lint

test: python-test site-test

build:
    just generate
    just site-build

ci-local: lint test
    just build
