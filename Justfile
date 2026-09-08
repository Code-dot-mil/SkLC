export UV_CACHE_DIR := ".uv-cache"

default:
    just --list

site_root := "products/deployment-kit/site"
local_generated := "maintainer/exchange/local-generated"

generate scan_mode="static-only":
    uv run python -m skill_exchange.cli publish-local --generated-dir {{local_generated}} --scan-mode {{scan_mode}}

python-lint:
    uv run --extra test ruff check maintainer tests

python-lint-fix:
    uv run --extra test ruff check --fix maintainer tests

python-test:
    uv run --extra test pytest

site-lint:
    npm --prefix {{site_root}} run lint

site-test:
    npm --prefix {{site_root}} run test

site-build:
    SKILL_EXCHANGE_GENERATED_ROOT="$PWD/{{local_generated}}" npm --prefix {{site_root}} run build

lint: python-lint site-lint

test: python-test site-test

build scan_mode="static-only":
    just generate {{scan_mode}}
    just site-build

ci-local scan_mode="static-only": lint test
    just build {{scan_mode}}
