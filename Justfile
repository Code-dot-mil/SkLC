export UV_CACHE_DIR := ".uv-cache"

default:
    just --list

local_generated := ".exchange/local-generated"

generate:
    uv run python -m skill_exchange.cli generate \
        --skills products/skill-catalog --evidence products/skill-catalog-assessments \
        --generated {{local_generated}}

python-lint:
    uv run --extra test ruff check maintainer products

python-lint-fix:
    uv run --extra test ruff check --fix maintainer products

python-test:
    uv run --extra test pytest

site-lint:
    npm --prefix products/deployment-kit/operator/site run lint

site-test:
    npm --prefix products/deployment-kit/operator/site run test

site-build:
    SKILL_EXCHANGE_GENERATED_ROOT="$PWD/{{local_generated}}" npm --prefix products/deployment-kit/operator/site run build

lint: python-lint site-lint

test: python-test site-test

build:
    just generate
    just site-build

ci-local: lint test
    just build
