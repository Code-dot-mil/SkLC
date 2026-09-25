export UV_CACHE_DIR := ".uv-cache"

default:
    just --list

local_generated := ".exchange/local-generated"

generate scan_mode="static-only":
    uv run python -m skill_exchange.cli publish-local --generated-dir {{local_generated}} --scan-mode {{scan_mode}}

python-lint:
    uv run --extra test ruff check scripts tests products/assessment-kit

python-lint-fix:
    uv run --extra test ruff check --fix scripts tests products/assessment-kit

python-test:
    uv run --extra test pytest

site-lint:
    npm --prefix site run lint

site-test:
    npm --prefix site run test

site-build:
    SKILL_EXCHANGE_GENERATED_ROOT="$PWD/{{local_generated}}" npm --prefix site run build

lint: python-lint site-lint

test: python-test site-test

build scan_mode="static-only":
    just generate {{scan_mode}}
    just site-build

ci-local scan_mode="static-only": lint test
    just build {{scan_mode}}
