"""
ScrapeGuard — Web Scraper Module.

Handles all HTTP communication with target websites:
  • Dynamic random delays between requests (anti-ban)
  • User-Agent rotation from a configurable pool
  • Robust error handling (timeout, connection, HTTP errors)
  • CSS selector-based data extraction via BeautifulSoup
  • Retry logic with exponential back-off

This module NEVER raises unhandled exceptions — all errors are caught,
logged, and returned as structured error dicts.
"""

from __future__ import annotations

import random
import time
from typing import Any

import requests
from bs4 import BeautifulSoup

from config.settings import (
    MAX_RETRIES,
    REQUEST_DELAY_MAX,
    REQUEST_DELAY_MIN,
    REQUEST_TIMEOUT,
    RETRY_BACKOFF_FACTOR,
    USER_AGENTS,
)
from src.core.logger import logger
from src.schemas.base import TargetDefinition


# ===========================
# Helper Functions
# ===========================

def _get_random_headers() -> dict[str, str]:
    """
    Build HTTP headers with a randomly selected User-Agent.

    Returns:
        Dict of HTTP headers suitable for a browser-like request.
    """
    ua = random.choice(USER_AGENTS)
    return {
        "User-Agent": ua,
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;"
            "q=0.9,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "DNT": "1",
    }


def _apply_dynamic_delay() -> None:
    """
    Sleep for a random duration within the configured range.

    This prevents request patterns that could trigger WAF rate-limiting.
    """
    delay = random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX)
    logger.debug("Applying dynamic delay: {d:.2f}s", d=delay)
    time.sleep(delay)


# ===========================
# Core Scraping Functions
# ===========================

def fetch_page(url: str, retries: int = MAX_RETRIES) -> str | None:
    """
    Fetch the raw HTML content of a URL with retry logic.

    Implements exponential back-off on transient failures (timeouts,
    connection errors, 5xx status codes).

    Args:
        url: The target URL to fetch.
        retries: Maximum number of retry attempts.

    Returns:
        Raw HTML string on success, or ``None`` on permanent failure.
    """
    for attempt in range(1, retries + 1):
        try:
            _apply_dynamic_delay()
            headers = _get_random_headers()

            logger.info(
                "Fetching URL (attempt {att}/{max}): {url}",
                att=attempt, max=retries, url=url,
            )

            response = requests.get(
                url,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True,
            )
            response.raise_for_status()

            logger.info(
                "Successfully fetched {url} — status={status}, size={size} bytes",
                url=url,
                status=response.status_code,
                size=len(response.content),
            )
            return response.text

        except requests.exceptions.Timeout:
            logger.warning(
                "Timeout on attempt {att}/{max} for {url}",
                att=attempt, max=retries, url=url,
            )
        except requests.exceptions.ConnectionError:
            logger.warning(
                "Connection error on attempt {att}/{max} for {url}",
                att=attempt, max=retries, url=url,
            )
        except requests.exceptions.HTTPError as exc:
            status_code = exc.response.status_code if exc.response else "N/A"
            logger.warning(
                "HTTP {status} on attempt {att}/{max} for {url}",
                status=status_code, att=attempt, max=retries, url=url,
            )
            # Don't retry on client errors (4xx) — they won't self-resolve
            if exc.response is not None and 400 <= exc.response.status_code < 500:
                logger.error(
                    "Client error {status} is not retryable — aborting {url}",
                    status=exc.response.status_code, url=url,
                )
                return None
        except requests.exceptions.RequestException as exc:
            logger.error(
                "Unexpected request error on attempt {att}/{max} for {url}: {err}",
                att=attempt, max=retries, url=url, err=str(exc),
            )

        # Exponential back-off before next retry
        if attempt < retries:
            backoff = RETRY_BACKOFF_FACTOR * attempt
            logger.debug("Backing off for {b:.1f}s before retry", b=backoff)
            time.sleep(backoff)

    logger.error("All {max} attempts exhausted for {url}", max=retries, url=url)
    return None


def extract_data(
    html: str,
    selectors: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """
    Parse HTML and extract data using CSS selectors from a target definition.

    For each selector, extracts the **text content** of the first matching
    element.  If no element matches, the field value is set to ``None``.

    Args:
        html: Raw HTML string to parse.
        selectors: Selector dict from targets.json, e.g.::

            {"title": {"css": "h1", "type": "str", "required": true}}

    Returns:
        Dict mapping field names to extracted (string) values.
    """
    soup = BeautifulSoup(html, "lxml")
    extracted: dict[str, Any] = {}

    for field_name, rules in selectors.items():
        css_selector: str = rules["css"]
        element = soup.select_one(css_selector)

        if element is not None:
            raw_text = element.get_text(strip=True)
            extracted[field_name] = raw_text
            logger.debug(
                "Extracted '{field}': '{value}' (selector: {css})",
                field=field_name, value=raw_text[:80], css=css_selector,
            )
        else:
            extracted[field_name] = None
            logger.warning(
                "No element found for '{field}' with selector '{css}'",
                field=field_name, css=css_selector,
            )

    return extracted


def scrape_target(target: TargetDefinition) -> dict[str, Any] | None:
    """
    End-to-end scraping pipeline for a single target.

    Orchestrates: fetch → parse → extract.

    Args:
        target: A validated ``TargetDefinition`` object.

    Returns:
        Extracted data dict on success, or ``None`` on fetch failure.
    """
    logger.info(
        "Starting scrape for target '{name}' → {url}",
        name=target.name, url=target.url,
    )

    html = fetch_page(target.url)
    if html is None:
        logger.error(
            "Scrape FAILED for target '{name}' — no HTML retrieved",
            name=target.name,
        )
        return None

    data = extract_data(html, target.selectors)
    logger.info(
        "Scrape COMPLETE for target '{name}' — {n} fields extracted",
        name=target.name, n=len(data),
    )
    return data
