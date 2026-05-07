"""
ScrapeGuard — Dynamic Pydantic Model Factory.

Builds runtime Pydantic v2 models from the selector definitions stored
in ``targets.json``.  Each target's ``selectors`` dict is translated into
a strictly-typed BaseModel via ``pydantic.create_model``.

Workflow:
    targets.json  →  build_model_from_selectors()  →  Pydantic BaseModel subclass
                                                         ↕
    scraped dict  →  Model(**scraped)  →  ✅ valid  /  ❌ ValidationError
"""

from __future__ import annotations

import json
from typing import Any, Optional

from pydantic import create_model, BaseModel

from config.settings import TARGETS_FILE
from src.core.logger import logger


# ===========================
# Type Mapping
# ===========================

TYPE_MAP: dict[str, type] = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
}


# ===========================
# Target Data Structure
# ===========================

class TargetDefinition(BaseModel):
    """
    Represents a single scraping target loaded from targets.json.

    Attributes:
        name: Unique identifier for the target.
        url: The URL to scrape.
        selectors: Mapping of field_name → {css, type, required}.
        schedule_minutes: Interval between scrape cycles.
    """

    name: str
    url: str
    selectors: dict[str, dict[str, Any]]
    schedule_minutes: int = 60


# ===========================
# Dynamic Model Factory
# ===========================

def build_model_from_selectors(
    target_name: str,
    selectors: dict[str, dict[str, Any]],
) -> type[BaseModel]:
    """
    Dynamically create a Pydantic BaseModel from selector definitions.

    For each selector entry:
      • ``required: true``  → field is mandatory (no default).
      • ``required: false`` → field is ``Optional[T]`` with default ``None``.

    Args:
        target_name: Human-readable name used as the model class name.
        selectors: Selector dict from targets.json, e.g.::

            {
                "title": {"css": "h1", "type": "str", "required": true},
                "price": {"css": ".price", "type": "float", "required": false}
            }

    Returns:
        A new Pydantic model class with the specified fields.

    Raises:
        ValueError: If a selector references an unsupported type string.
    """
    field_definitions: dict[str, Any] = {}

    for field_name, rules in selectors.items():
        type_str: str = rules.get("type", "str")
        python_type = TYPE_MAP.get(type_str)

        if python_type is None:
            raise ValueError(
                f"Unsupported type '{type_str}' for field '{field_name}' "
                f"in target '{target_name}'. Supported: {list(TYPE_MAP.keys())}"
            )

        is_required: bool = rules.get("required", True)

        if is_required:
            # Ellipsis (...) signals a required field in create_model
            field_definitions[field_name] = (python_type, ...)
        else:
            field_definitions[field_name] = (Optional[python_type], None)

    model = create_model(target_name, **field_definitions)
    logger.debug(
        "Built dynamic model '{name}' with fields: {fields}",
        name=target_name,
        fields=list(field_definitions.keys()),
    )
    return model


def load_targets() -> list[TargetDefinition]:
    """
    Load and validate all target definitions from ``targets.json``.

    Returns:
        A list of validated ``TargetDefinition`` objects.

    Raises:
        FileNotFoundError: If targets.json does not exist.
        json.JSONDecodeError: If the file contains malformed JSON.
    """
    logger.info("Loading targets from {path}", path=TARGETS_FILE)

    with open(TARGETS_FILE, "r", encoding="utf-8") as fh:
        raw: dict = json.load(fh)

    targets: list[TargetDefinition] = []
    for entry in raw.get("targets", []):
        target = TargetDefinition(**entry)
        targets.append(target)
        logger.debug("Loaded target: {name} → {url}", name=target.name, url=target.url)

    logger.info("Total targets loaded: {count}", count=len(targets))
    return targets


def build_models_for_targets(
    targets: list[TargetDefinition],
) -> dict[str, type[BaseModel]]:
    """
    Build Pydantic models for every target in the list.

    Args:
        targets: List of ``TargetDefinition`` objects.

    Returns:
        Dict mapping ``target.name`` → dynamically created Pydantic model.
    """
    models: dict[str, type[BaseModel]] = {}
    for target in targets:
        models[target.name] = build_model_from_selectors(
            target_name=target.name,
            selectors=target.selectors,
        )
    return models
