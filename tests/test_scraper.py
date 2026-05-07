"""
ScrapeGuard — Scraper Unit Tests.

Run:  pytest tests/test_scraper.py -v
"""

from __future__ import annotations
from unittest.mock import patch, MagicMock
import pytest
import responses
import requests

from src.core.scraper import (
    _get_random_headers,
    extract_data,
    fetch_page,
    scrape_target,
)
from src.schemas.base import TargetDefinition

SAMPLE_HTML = """
<!DOCTYPE html>
<html><head><title>Test</title></head>
<body>
  <h1 class="main-title">Hello ScrapeGuard</h1>
  <span class="price">49.99</span>
  <div class="stock-info">142</div>
</body></html>
"""

SAMPLE_TARGET = TargetDefinition(
    name="test_target",
    url="https://test.example.com/page",
    selectors={
        "title": {"css": "h1.main-title", "type": "str", "required": True},
        "price": {"css": "span.price", "type": "float", "required": True},
        "stock": {"css": "div.stock-info", "type": "int", "required": False},
    },
    schedule_minutes=60,
)


class TestGetRandomHeaders:
    def test_returns_dict(self) -> None:
        assert isinstance(_get_random_headers(), dict)

    def test_contains_user_agent(self) -> None:
        h = _get_random_headers()
        assert "User-Agent" in h and len(h["User-Agent"]) > 10

    def test_user_agent_varies(self) -> None:
        agents = {_get_random_headers()["User-Agent"] for _ in range(50)}
        assert len(agents) > 1


class TestFetchPage:
    @responses.activate
    @patch("src.core.scraper._apply_dynamic_delay")
    def test_successful_fetch(self, mock_delay: MagicMock) -> None:
        responses.add(responses.GET, "https://test.example.com/page", body=SAMPLE_HTML, status=200)
        result = fetch_page("https://test.example.com/page", retries=1)
        assert result is not None
        assert "Hello ScrapeGuard" in result

    @responses.activate
    @patch("src.core.scraper._apply_dynamic_delay")
    def test_404_returns_none(self, mock_delay: MagicMock) -> None:
        responses.add(responses.GET, "https://test.example.com/x", status=404)
        assert fetch_page("https://test.example.com/x", retries=3) is None

    @patch("src.core.scraper._apply_dynamic_delay")
    @patch("src.core.scraper.requests.get")
    @patch("src.core.scraper.time.sleep")
    def test_timeout_handled(self, ms: MagicMock, mg: MagicMock, md: MagicMock) -> None:
        mg.side_effect = requests.exceptions.Timeout("timeout")
        assert fetch_page("https://test.example.com/slow", retries=2) is None

    @patch("src.core.scraper._apply_dynamic_delay")
    @patch("src.core.scraper.requests.get")
    @patch("src.core.scraper.time.sleep")
    def test_connection_error_handled(self, ms: MagicMock, mg: MagicMock, md: MagicMock) -> None:
        mg.side_effect = requests.exceptions.ConnectionError("DNS")
        assert fetch_page("https://test.example.com/d", retries=1) is None


class TestExtractData:
    def test_extracts_all_fields(self) -> None:
        sel = {"title": {"css": "h1.main-title", "type": "str", "required": True}}
        data = extract_data(SAMPLE_HTML, sel)
        assert data["title"] == "Hello ScrapeGuard"

    def test_missing_selector_returns_none(self) -> None:
        sel = {"x": {"css": "div.nope", "type": "str", "required": True}}
        assert extract_data(SAMPLE_HTML, sel)["x"] is None


class TestScrapeTarget:
    @responses.activate
    @patch("src.core.scraper._apply_dynamic_delay")
    def test_success(self, md: MagicMock) -> None:
        responses.add(responses.GET, SAMPLE_TARGET.url, body=SAMPLE_HTML, status=200)
        result = scrape_target(SAMPLE_TARGET)
        assert result is not None and result["title"] == "Hello ScrapeGuard"

    @patch("src.core.scraper._apply_dynamic_delay")
    @patch("src.core.scraper.requests.get")
    @patch("src.core.scraper.time.sleep")
    def test_failure_returns_none(self, ms: MagicMock, mg: MagicMock, md: MagicMock) -> None:
        mg.side_effect = requests.exceptions.ConnectionError("Refused")
        assert scrape_target(SAMPLE_TARGET) is None
