"""
ScrapeGuard — Pydantic Validation Checkpoint.

Validates scraped data dicts against dynamically-generated Pydantic models.
Every validation attempt is logged; ``ValidationError`` exceptions are
caught, structured, and returned — they are **never** re-raised.

This module acts as the bridge between raw scraper output and the
integrity report consumed by the dashboard.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ValidationError

from src.core.logger import logger
from src.schemas.base import (
    TargetDefinition,
    build_model_from_selectors,
)


# ===========================
# Result Data Structures
# ===========================

class ValidationResult(BaseModel):
    """
    Structured outcome of a single validation run.

    Attributes:
        target_name: Identifier of the validated target.
        url: The scraped URL.
        status: One of ``HEALTHY``, ``SCHEMA_BROKEN``, ``CONNECTION_ERROR``.
        timestamp: ISO-8601 timestamp of the validation.
        errors: List of human-readable error descriptions (empty on success).
        extracted_data: The raw scraped data dict (for debugging).
    """

    target_name: str
    url: str
    status: str
    timestamp: str
    errors: list[str] = []
    extracted_data: dict[str, Any] = {}


# ===========================
# Status Constants
# ===========================

STATUS_HEALTHY: str = "HEALTHY"
STATUS_SCHEMA_BROKEN: str = "SCHEMA_BROKEN"
STATUS_CONNECTION_ERROR: str = "CONNECTION_ERROR"


# ===========================
# Core Validation Logic
# ===========================

def _coerce_value(raw_value: Any, expected_type: str) -> Any:
    """
    Attempt to coerce a raw scraped string into the expected Python type.

    CSS selectors always produce strings, so we need type coercion before
    Pydantic validation when the expected type is numeric or boolean.

    Args:
        raw_value: The value extracted by the scraper (usually a string).
        expected_type: Type string from targets.json (``str``, ``int``, etc.).

    Returns:
        Coerced value, or the original value if coercion fails.
    """
    if raw_value is None:
        return None

    coercion_map: dict[str, type] = {
        "int": int,
        "float": float,
        "bool": bool,
    }

    target_type = coercion_map.get(expected_type)
    if target_type is None:
        # "str" or unknown — return as-is
        return raw_value

    try:
        # Special handling for bool: "true"/"false"/"1"/"0"
        if target_type is bool:
            return str(raw_value).strip().lower() in ("true", "1", "yes")
        return target_type(raw_value)
    except (ValueError, TypeError) as exc:
        logger.warning(
            "Type coercion failed: '{val}' → {t} — {err}",
            val=raw_value, t=expected_type, err=str(exc),
        )
        return raw_value


def validate_scraped_data(
    target: TargetDefinition,
    scraped_data: dict[str, Any] | None,
) -> ValidationResult:
    """
    Validate scraped data against the target's dynamic Pydantic schema.

    Workflow:
        1. If ``scraped_data`` is None → CONNECTION_ERROR.
        2. Coerce raw string values to expected types.
        3. Build a dynamic Pydantic model from target selectors.
        4. Instantiate the model — catch ``ValidationError`` if schema is broken.
        5. Return a structured ``ValidationResult``.

    Args:
        target: The target definition containing selectors and rules.
        scraped_data: Data dict from the scraper, or None on fetch failure.

    Returns:
        A ``ValidationResult`` with status, errors, and extracted data.
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    # --- Case 1: Scraper failed to fetch any data ---
    if scraped_data is None:
        logger.error(
            "Validation skipped for '{name}' — no data (connection failure)",
            name=target.name,
        )
        return ValidationResult(
            target_name=target.name,
            url=target.url,
            status=STATUS_CONNECTION_ERROR,
            timestamp=timestamp,
            errors=["Connection failed — no HTML data retrieved."],
            extracted_data={},
        )

    # --- Case 2: Coerce types before validation ---
    coerced_data: dict[str, Any] = {}
    for field_name, value in scraped_data.items():
        expected_type = target.selectors.get(field_name, {}).get("type", "str")
        coerced_data[field_name] = _coerce_value(value, expected_type)

    # --- Case 3: Build model & validate ---
    try:
        model_cls = build_model_from_selectors(target.name, target.selectors)
        model_cls(**coerced_data)

        logger.info(
            "✅ Validation PASSED for '{name}' — all fields match schema",
            name=target.name,
        )
        return ValidationResult(
            target_name=target.name,
            url=target.url,
            status=STATUS_HEALTHY,
            timestamp=timestamp,
            errors=[],
            extracted_data=coerced_data,
        )

    except ValidationError as exc:
        error_messages = [
            f"Field '{e['loc'][0]}': {e['msg']}" if e.get("loc") else e["msg"]
            for e in exc.errors()
        ]
        logger.warning(
            "❌ Validation FAILED for '{name}' — {n} error(s): {errs}",
            name=target.name,
            n=len(error_messages),
            errs=error_messages,
        )
        return ValidationResult(
            target_name=target.name,
            url=target.url,
            status=STATUS_SCHEMA_BROKEN,
            timestamp=timestamp,
            errors=error_messages,
            extracted_data=coerced_data,
        )

    except Exception as exc:
        # Catch-all safety net — validator must never crash
        logger.exception(
            "Unexpected error during validation for '{name}': {err}",
            name=target.name, err=str(exc),
        )
        return ValidationResult(
            target_name=target.name,
            url=target.url,
            status=STATUS_SCHEMA_BROKEN,
            timestamp=timestamp,
            errors=[f"Unexpected validation error: {str(exc)}"],
            extracted_data=coerced_data if coerced_data else {},
        )
