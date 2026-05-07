"""
ScrapeGuard — Validator Unit Tests.

Run:  pytest tests/test_validator.py -v
"""

from __future__ import annotations
from typing import Any
import pytest

from src.core.validator import (
    ValidationResult,
    _coerce_value,
    validate_scraped_data,
    STATUS_HEALTHY,
    STATUS_SCHEMA_BROKEN,
    STATUS_CONNECTION_ERROR,
)
from src.schemas.base import TargetDefinition, build_model_from_selectors


SAMPLE_TARGET = TargetDefinition(
    name="val_test",
    url="https://example.com",
    selectors={
        "title": {"css": "h1", "type": "str", "required": True},
        "price": {"css": ".price", "type": "float", "required": True},
        "stock": {"css": ".stock", "type": "int", "required": False},
    },
    schedule_minutes=60,
)


class TestCoerceValue:
    """Tests for type coercion helper."""

    def test_str_passthrough(self) -> None:
        assert _coerce_value("hello", "str") == "hello"

    def test_int_coercion(self) -> None:
        assert _coerce_value("42", "int") == 42

    def test_float_coercion(self) -> None:
        assert _coerce_value("3.14", "float") == pytest.approx(3.14)

    def test_bool_coercion_true(self) -> None:
        assert _coerce_value("true", "bool") is True

    def test_bool_coercion_false(self) -> None:
        assert _coerce_value("no", "bool") is False

    def test_none_passthrough(self) -> None:
        assert _coerce_value(None, "int") is None

    def test_invalid_coercion_returns_original(self) -> None:
        result = _coerce_value("not_a_number", "int")
        assert result == "not_a_number"


class TestBuildModelFromSelectors:
    """Tests for dynamic Pydantic model creation."""

    def test_creates_valid_model(self) -> None:
        model = build_model_from_selectors("TestModel", SAMPLE_TARGET.selectors)
        instance = model(title="Test", price=9.99, stock=5)
        assert instance.title == "Test"

    def test_required_field_missing_raises(self) -> None:
        model = build_model_from_selectors("TestModel", SAMPLE_TARGET.selectors)
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            model(stock=5)  # title and price are required

    def test_optional_field_defaults_none(self) -> None:
        model = build_model_from_selectors("TestModel", SAMPLE_TARGET.selectors)
        instance = model(title="T", price=1.0)
        assert instance.stock is None

    def test_unsupported_type_raises_value_error(self) -> None:
        bad_selectors = {"x": {"css": "p", "type": "datetime", "required": True}}
        with pytest.raises(ValueError, match="Unsupported type"):
            build_model_from_selectors("Bad", bad_selectors)


class TestValidateScrapedData:
    """Tests for the full validation pipeline."""

    def test_healthy_result(self) -> None:
        data = {"title": "Product", "price": "29.99", "stock": "10"}
        result = validate_scraped_data(SAMPLE_TARGET, data)
        assert result.status == STATUS_HEALTHY
        assert result.errors == []

    def test_connection_error_on_none(self) -> None:
        result = validate_scraped_data(SAMPLE_TARGET, None)
        assert result.status == STATUS_CONNECTION_ERROR
        assert len(result.errors) > 0

    def test_schema_broken_on_missing_required(self) -> None:
        data = {"stock": "5"}  # title and price missing
        result = validate_scraped_data(SAMPLE_TARGET, data)
        assert result.status == STATUS_SCHEMA_BROKEN
        assert len(result.errors) > 0

    def test_schema_broken_on_none_required_field(self) -> None:
        data = {"title": None, "price": "10.0"}
        result = validate_scraped_data(SAMPLE_TARGET, data)
        assert result.status == STATUS_SCHEMA_BROKEN

    def test_result_contains_timestamp(self) -> None:
        data = {"title": "X", "price": "1.0"}
        result = validate_scraped_data(SAMPLE_TARGET, data)
        assert result.timestamp is not None
        assert "T" in result.timestamp  # ISO format

    def test_result_is_validation_result_type(self) -> None:
        data = {"title": "X", "price": "1.0"}
        result = validate_scraped_data(SAMPLE_TARGET, data)
        assert isinstance(result, ValidationResult)
