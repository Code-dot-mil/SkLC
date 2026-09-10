from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ExchangePolicy:
    categories: frozenset[str]
    tags: frozenset[str]
    show_unknown_risk: bool
    show_confidence_flags: bool
    default_sort: str


def load_exchange_policy(exchange_dir: Path) -> ExchangePolicy:
    categories_yaml = _load_yaml(exchange_dir / "categories.yaml")
    tags_yaml = _load_yaml(exchange_dir / "tags.yaml")
    display_yaml = _load_yaml(exchange_dir / "display-policy.yaml")

    categories = frozenset(str(item["id"]) for item in categories_yaml.get("categories", []))
    tags = frozenset(str(item) for item in tags_yaml.get("tags", []))

    return ExchangePolicy(
        categories=categories,
        tags=tags,
        show_unknown_risk=bool(display_yaml.get("show_unknown_risk", False)),
        show_confidence_flags=bool(display_yaml.get("show_confidence_flags", True)),
        default_sort=str(display_yaml.get("default_sort", "name")),
    )


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    loaded = yaml.safe_load(path.read_text()) or {}
    if not isinstance(loaded, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return loaded
