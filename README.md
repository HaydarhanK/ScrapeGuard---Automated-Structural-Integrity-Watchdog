# 🛡️ ScrapeGuard — Automated Structural Integrity Watchdog

> A production-ready Python watchdog system that periodically scrapes target URLs, validates the extracted data against dynamic Pydantic schemas, and reports structural changes via a real-time Streamlit dashboard.

---

## 📋 Table of Contents

1. [Summary](#-summary)
2. [Technologies Used](#-technologies-used)
3. [Architectural Structure](#-architectural-structure)
4. [Methodology & Mechanics](#-methodology--mechanics)
5. [Installation Steps](#-installation-steps)
6. [License](#-license)

---

## 🎯 Summary

**ScrapeGuard** is a structural integrity monitoring tool designed for web data pipelines. It continuously watches configured target URLs and detects when a website's DOM structure changes in ways that would break your data extraction logic.

**Key Features:**
- 🔄 **Automated Scheduling** — Configurable per-target scrape intervals
- 🛡️ **Dynamic Schema Validation** — Pydantic models generated at runtime from JSON config
- 🎨 **Real-time Dashboard** — Premium Streamlit UI showing target health at a glance
- 📊 **Structured Logging** — Loguru with rotation & retention (no disk bloat)
- 🕶️ **Anti-Ban Measures** — Dynamic delays, User-Agent rotation, retry with backoff
- 🧪 **Fully Tested** — pytest suite with mocked HTTP responses

---

## 🛠️ Technologies Used

| Technology | Version | Purpose |
|---|---|---|
| **Python** | 3.11+ | Core runtime |
| **Requests** | 2.31+ | HTTP client with session management |
| **BeautifulSoup4** | 4.12+ | HTML parsing & CSS selector extraction |
| **lxml** | 5.1+ | Fast HTML parser backend |
| **Pydantic** | 2.5+ | Dynamic data validation & typing |
| **Loguru** | 0.7+ | Structured logging with rotation |
| **Streamlit** | 1.30+ | Interactive web dashboard |
| **Schedule** | 1.2+ | Lightweight task scheduling |
| **pytest** | 8.0+ | Testing framework |
| **pytest-mock** | 3.12+ | Mock utilities for pytest |
| **responses** | 0.25+ | HTTP response mocking for tests |

---

## 🏗️ Architectural Structure

```
ScrapeGuard/
├── app.py                    # Streamlit dashboard (read-only viewer)
├── main_engine.py            # Background orchestrator / scheduler
├── run_dashboard.py          # Root launcher — sets PYTHONPATH & starts Streamlit
├── config/
│   ├── __init__.py
│   ├── targets.json          # Target URLs, CSS selectors, type rules
│   └── settings.py           # Global configuration constants
├── src/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── scraper.py        # HTTP fetch + CSS extraction engine
│   │   ├── validator.py      # Pydantic validation checkpoint
│   │   └── logger.py         # Loguru rotation/retention setup
│   └── schemas/
│       ├── __init__.py
│       └── base.py           # Dynamic Pydantic model factory
├── tests/
│   ├── __init__.py
│   ├── test_scraper.py       # Scraper unit tests
│   └── test_validator.py     # Validator unit tests
├── logs/                     # Auto-generated, git-ignored
├── .env                      # Environment variables (git-ignored)
├── .gitignore
├── pyproject.toml            # Package metadata & build config
├── pyrightconfig.json        # Type-checker settings for IDE support
├── requirements.txt
├── README.md                 # This file
└── README_TR.md              # Turkish documentation
```

### Separation of Concerns

| Component | Responsibility |
|---|---|
| `main_engine.py` | Independent scheduler — runs scrape cycles in background |
| `app.py` | Pure viewer — reads JSON results & log files from disk |
| `run_dashboard.py` | Root launcher — ensures correct PYTHONPATH for Streamlit |
| `validator.py` | Bridges scraper output ↔ dynamic Pydantic models |
| `base.py` | Factory that builds Pydantic models from `targets.json` at runtime |

---

## ⚙️ Methodology & Mechanics

### 1. Dynamic Schema Generation
Target definitions in `targets.json` specify CSS selectors with expected types. At runtime, `base.py` uses `pydantic.create_model()` to build typed models dynamically — no hardcoded schemas needed.

### 2. Anti-Ban Scraping
- **Dynamic delays**: `time.sleep(random.uniform(2, 5))` between requests
- **User-Agent rotation**: 6 browser-like UAs selected randomly per request
- **Exponential backoff**: Retry with increasing delays on transient failures
- **Graceful error handling**: Timeout, ConnectionError, and HTTP errors are caught — the scraper never crashes

### 3. Validation Pipeline
```
Scraper → Raw Dict → Type Coercion → Dynamic Pydantic Model → Result
                                                                 ├── ✅ HEALTHY
                                                                 ├── ❌ SCHEMA_BROKEN
                                                                 └── ⚠️ CONNECTION_ERROR
```

### 4. Decoupled Architecture
The engine (`main_engine.py`) writes results to `latest_results.json`. The dashboard (`app.py`) only reads this file. Both live in the project root. A dedicated launcher (`run_dashboard.py`) ensures the correct `PYTHONPATH` is set so that all `config.*` and `src.*` imports resolve properly.

### 5. Log Management
Loguru configured with **10 MB rotation** and **7-day retention**. Old logs are compressed to `.zip`. Thread-safe via `enqueue=True`.

---

## 🚀 Installation Steps

### Prerequisites
- Python 3.11 or higher
- pip package manager

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/ScrapeGuard.git
cd ScrapeGuard
```

### 2. Create a Virtual Environment
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Install in Editable Mode
```bash
pip install -e .
```
This registers the `config` and `src` packages so that absolute imports work correctly regardless of which directory you run scripts from.

### 5. Configure Targets
Edit `config/targets.json` to add your target URLs and CSS selectors.

### 6. Run the Engine (Background)
```bash
python main_engine.py
```

### 7. Launch the Dashboard
```bash
python run_dashboard.py
```
> **Note:** Always use `run_dashboard.py` instead of calling `streamlit run app.py` directly. The launcher sets the required `PYTHONPATH` automatically.

### 8. Run Tests
```bash
pytest tests/ -v
```

---

## 📄 License

This project is licensed under the **MIT License**.

```
MIT License

Copyright (c) 2026 ScrapeGuard

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
```
