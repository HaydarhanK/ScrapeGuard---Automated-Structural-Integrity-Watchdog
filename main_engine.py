"""
ScrapeGuard — Main Engine / Orchestrator.

This module is the **independent background scheduler** that:
  1. Loads all targets from ``targets.json``.
  2. Runs scrape → validate cycles on a configurable schedule.
  3. Persists results to ``latest_results.json`` (consumed by dashboard).
  4. Operates independently of the Streamlit UI.

Usage (standalone):
    python main_engine.py

The engine writes results to disk; the dashboard reads them.
This decoupled architecture ensures the UI never blocks on I/O.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from typing import Any

import schedule

from config.settings import DEFAULT_SCHEDULE_MINUTES, RESULTS_FILE
from src.core.logger import logger
from src.core.scraper import scrape_target
from src.core.validator import (
    ValidationResult,
    validate_scraped_data,
)
from src.schemas.base import TargetDefinition, load_targets


# ===========================
# Result Persistence
# ===========================

def _save_results(results: list[ValidationResult]) -> None:
    """
    Persist validation results to the JSON file read by the dashboard.

    Atomically writes by first writing to a temp file, then replacing.

    Args:
        results: List of ``ValidationResult`` objects from the current cycle.
    """
    payload: dict[str, Any] = {
        "last_run": datetime.now(timezone.utc).isoformat(),
        "results": [r.model_dump() for r in results],
    }

    tmp_path = RESULTS_FILE.with_suffix(".tmp")
    try:
        tmp_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp_path.replace(RESULTS_FILE)
        logger.info("Results saved to {path}", path=RESULTS_FILE)
    except OSError as exc:
        logger.error("Failed to save results: {err}", err=str(exc))


def _load_saved_results() -> dict[str, Any]:
    """
    Load the most recent results from disk.

    Returns:
        Parsed JSON dict, or an empty structure if file doesn't exist.
    """
    if not RESULTS_FILE.exists():
        return {"last_run": None, "results": []}

    try:
        raw = RESULTS_FILE.read_text(encoding="utf-8")
        return json.loads(raw)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not load saved results: {err}", err=str(exc))
        return {"last_run": None, "results": []}


# ===========================
# Scrape-Validate Cycle
# ===========================

def run_single_target(target: TargetDefinition) -> ValidationResult:
    """
    Execute a full scrape → validate cycle for one target.

    Args:
        target: The target to process.

    Returns:
        Validation result for this target.
    """
    logger.info("──── Processing target: {name} ────", name=target.name)
    scraped_data = scrape_target(target)
    result = validate_scraped_data(target, scraped_data)
    logger.info(
        "Result for '{name}': {status}",
        name=target.name,
        status=result.status,
    )
    return result


def run_full_cycle(targets: list[TargetDefinition] | None = None) -> list[ValidationResult]:
    """
    Execute a scrape → validate cycle for ALL targets.

    This is the main entry point called by the scheduler and the
    dashboard's "Test All" button.

    Args:
        targets: Optional pre-loaded targets. If None, loads from disk.

    Returns:
        List of ``ValidationResult`` objects.
    """
    if targets is None:
        targets = load_targets()

    logger.info("═══════ Starting full scrape cycle ({n} targets) ═══════", n=len(targets))
    results: list[ValidationResult] = []

    for target in targets:
        result = run_single_target(target)
        results.append(result)

    _save_results(results)

    # Summary
    healthy = sum(1 for r in results if r.status == "HEALTHY")
    broken = sum(1 for r in results if r.status == "SCHEMA_BROKEN")
    errors = sum(1 for r in results if r.status == "CONNECTION_ERROR")
    logger.info(
        "═══════ Cycle complete — ✅ {h} healthy, ❌ {b} broken, ⚠️ {e} errors ═══════",
        h=healthy, b=broken, e=errors,
    )
    return results


# ===========================
# Scheduler Setup
# ===========================

def _setup_scheduler(targets: list[TargetDefinition]) -> None:
    """
    Register each target with the ``schedule`` library based on its
    ``schedule_minutes`` value.

    Args:
        targets: List of target definitions.
    """
    for target in targets:
        interval = target.schedule_minutes or DEFAULT_SCHEDULE_MINUTES
        schedule.every(interval).minutes.do(run_single_target, target=target)
        logger.info(
            "Scheduled '{name}' every {m} minute(s)",
            name=target.name, m=interval,
        )


def start_engine() -> None:
    """
    Main entry point for the background engine.

    1. Loads targets.
    2. Runs an initial full cycle immediately.
    3. Sets up the periodic scheduler.
    4. Enters the infinite scheduler loop.
    """
    logger.info("🚀 ScrapeGuard Engine starting...")

    targets = load_targets()
    if not targets:
        logger.error("No targets found in targets.json — engine cannot start.")
        sys.exit(1)

    # Initial full run
    run_full_cycle(targets)

    # Schedule subsequent runs
    _setup_scheduler(targets)

    logger.info("Engine is now running. Press Ctrl+C to stop.")
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("🛑 Engine stopped by user (KeyboardInterrupt).")
        sys.exit(0)


# ===========================
# CLI Entry Point
# ===========================

if __name__ == "__main__":
    start_engine()
