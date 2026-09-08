from pathlib import Path

REPOSITORY_ROOT = Path(__file__).parents[1]


def test_repository_uses_product_and_maintainer_boundaries() -> None:
    required = (
        "contracts",
        "products/assessment-kit",
        "products/skill-catalog/skills",
        "products/deployment-kit/site",
        "products/deployment-kit/prebuilt",
        "products/deployment-kit/operator",
        "maintainer/exchange",
        "maintainer/skill_exchange",
    )
    legacy = (".exchange", ".skill-lifecycle", "scripts", "site", "skills")

    assert all((REPOSITORY_ROOT / path).is_dir() for path in required)
    assert all(not (REPOSITORY_ROOT / path).exists() for path in legacy)

    catalog_skills = REPOSITORY_ROOT / "products" / "skill-catalog" / "skills" / "ai4sdlc"
    assert {path.name for path in catalog_skills.iterdir() if path.is_dir()} == {
        "code-change-description",
        "inline-documentation",
        "python-secure-code-review",
        "unit-test-generation",
    }


def test_prebuilt_source_contains_only_deployment_inputs() -> None:
    prebuilt = REPOSITORY_ROOT / "products" / "deployment-kit" / "prebuilt"

    assert {path.name for path in prebuilt.iterdir()} == {".gitlab-ci.yml", "README.md", "docs"}
    assert {path.name for path in (prebuilt / "docs").iterdir()} == {
        "deploy-gitlab-pages.md",
        "deploy-static-hosting.md",
        "install.md",
    }
