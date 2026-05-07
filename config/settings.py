"""
ScrapeGuard — Global Settings & Configuration Constants.

Centralizes all tunable parameters for scraping behaviour, rate-limiting,
timeout thresholds, log rotation policies, and file paths used across the
entire application.
"""

from pathlib import Path

# ===========================
# Path Configuration
# ===========================

# Project root is two levels up from this file (config/ → project root)
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
CONFIG_DIR: Path = PROJECT_ROOT / "config"
LOGS_DIR: Path = PROJECT_ROOT / "logs"
TARGETS_FILE: Path = CONFIG_DIR / "targets.json"

# Ensure the logs directory exists at import time
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# ===========================
# Scraper Settings
# ===========================

# Dynamic delay range (seconds) between consecutive requests
REQUEST_DELAY_MIN: float = 2.0
REQUEST_DELAY_MAX: float = 5.0

# HTTP request timeout (seconds) — connect + read
REQUEST_TIMEOUT: int = 15

# Maximum retry attempts per target on transient errors
MAX_RETRIES: int = 3

# Back-off multiplier for retries (seconds × attempt number)
RETRY_BACKOFF_FACTOR: float = 1.5

# ===========================
# User-Agent Rotation Pool
# ===========================

USER_AGENTS: list[str] = [
    # Chrome (Windows)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    # Firefox (Windows)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) "
    "Gecko/20100101 Firefox/125.0",
    # Edge (Windows)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    # Chrome (macOS)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    # Safari (macOS)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    # Chrome (Linux)
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

# ===========================
# Logging Configuration
# ===========================

# Log file path template (Loguru handles rotation numbering)
LOG_FILE_PATH: str = str(LOGS_DIR / "scrapeguard_{time:YYYY-MM-DD}.log")

# Maximum size per log file before rotation
LOG_ROTATION: str = "10 MB"

# How long to keep old log files
LOG_RETENTION: str = "7 days"

# Log format pattern
LOG_FORMAT: str = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> — "
    "<level>{message}</level>"
)

# Log level for file sink
LOG_LEVEL: str = "DEBUG"

# ===========================
# Scheduler Settings
# ===========================

# Default interval (minutes) if a target omits 'schedule_minutes'
DEFAULT_SCHEDULE_MINUTES: int = 60

# ===========================
# Streamlit Dashboard Settings
# ===========================

# How many recent log lines to display in the dashboard terminal
DASHBOARD_LOG_LINES: int = 150

# Auto-refresh interval for the dashboard (seconds)
DASHBOARD_REFRESH_SECONDS: int = 30

# Result storage file (written by engine, read by dashboard)
RESULTS_FILE: Path = LOGS_DIR / "latest_results.json"
