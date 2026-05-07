"""
ScrapeGuard — Streamlit Dashboard (Read-Only Viewer).

This dashboard is a **pure viewer** that reads results and logs from disk.
It does NOT run the scraping engine internally. The only active operation
is the "Test All Targets" button, which invokes ``run_full_cycle()`` with
a spinner so the UI remains responsive.

Launch:
    streamlit run app.py
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import streamlit as st

from config.settings import (
    DASHBOARD_LOG_LINES,
    DASHBOARD_REFRESH_SECONDS,
    LOGS_DIR,
    RESULTS_FILE,
    TARGETS_FILE,
)

# ===========================
# Page Configuration
# ===========================

st.set_page_config(
    page_title="ScrapeGuard — Structural Integrity Watchdog",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ===========================
# Custom CSS
# ===========================

st.markdown("""
<style>
    /* --- Global --- */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    .stApp {
        font-family: 'Inter', sans-serif;
    }

    /* --- Header --- */
    .main-header {
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
        padding: 2rem 2.5rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    }
    .main-header h1 {
        color: #ffffff;
        font-size: 2rem;
        font-weight: 700;
        margin: 0 0 0.25rem 0;
        letter-spacing: -0.02em;
    }
    .main-header p {
        color: #a8a5c8;
        font-size: 1rem;
        margin: 0;
        font-weight: 300;
    }

    /* --- Status Cards --- */
    .status-card {
        border-radius: 14px;
        padding: 1.4rem;
        text-align: center;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        margin-bottom: 0.5rem;
    }
    .status-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.25);
    }
    .status-healthy {
        background: linear-gradient(135deg, #0d3b2e 0%, #11998e 100%);
        border-left: 5px solid #38ef7d;
    }
    .status-broken {
        background: linear-gradient(135deg, #3b0d0d 0%, #c0392b 100%);
        border-left: 5px solid #ff6b6b;
    }
    .status-error {
        background: linear-gradient(135deg, #3b2f0d 0%, #e67e22 100%);
        border-left: 5px solid #feca57;
    }
    .status-card .count {
        font-size: 2.8rem;
        font-weight: 700;
        color: #ffffff;
        line-height: 1;
    }
    .status-card .label {
        font-size: 0.85rem;
        color: rgba(255, 255, 255, 0.75);
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-top: 0.4rem;
    }

    /* --- Target Cards --- */
    .target-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 14px;
        padding: 1.3rem 1.6rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
        border-left: 5px solid #667eea;
        transition: transform 0.2s ease;
    }
    .target-card:hover {
        transform: translateX(4px);
    }
    .target-card .target-name {
        font-size: 1.15rem;
        font-weight: 600;
        color: #e2e8f0;
        margin-bottom: 0.3rem;
    }
    .target-card .target-url {
        font-size: 0.8rem;
        color: #667eea;
        word-break: break-all;
    }
    .target-card .target-time {
        font-size: 0.75rem;
        color: #718096;
        margin-top: 0.3rem;
    }

    /* --- Badge --- */
    .badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }
    .badge-healthy { background: #38ef7d33; color: #38ef7d; }
    .badge-broken  { background: #ff6b6b33; color: #ff6b6b; }
    .badge-error   { background: #feca5733; color: #feca57; }

    /* --- Log Terminal --- */
    .log-terminal {
        background: #0d1117;
        border: 1px solid #21262d;
        border-radius: 12px;
        padding: 1rem 1.2rem;
        font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace;
        font-size: 0.78rem;
        color: #c9d1d9;
        max-height: 500px;
        overflow-y: auto;
        line-height: 1.6;
        white-space: pre-wrap;
        word-break: break-word;
    }

    /* --- Sidebar --- */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f0c29 0%, #1a1a2e 100%);
    }
    [data-testid="stSidebar"] .stMarkdown {
        color: #c9d1d9;
    }

    /* --- Metric tweaks --- */
    [data-testid="stMetricValue"] {
        font-size: 1.4rem !important;
    }

    /* --- Divider --- */
    .section-divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, #667eea, transparent);
        margin: 1.5rem 0;
        border: none;
    }
</style>
""", unsafe_allow_html=True)


# ===========================
# Data Loaders
# ===========================

def load_results() -> dict:
    """Load the latest results JSON written by the engine."""
    if not RESULTS_FILE.exists():
        return {"last_run": None, "results": []}
    try:
        raw = RESULTS_FILE.read_text(encoding="utf-8")
        return json.loads(raw)
    except (json.JSONDecodeError, OSError):
        return {"last_run": None, "results": []}


def load_targets_config() -> list[dict]:
    """Load raw target definitions for the sidebar."""
    if not TARGETS_FILE.exists():
        return []
    try:
        raw = TARGETS_FILE.read_text(encoding="utf-8")
        return json.loads(raw).get("targets", [])
    except (json.JSONDecodeError, OSError):
        return []


def load_recent_logs(max_lines: int = DASHBOARD_LOG_LINES) -> str:
    """
    Read the most recent log lines from disk.

    Scans the logs directory for the newest .log file and returns
    the last ``max_lines`` lines.
    """
    log_files = sorted(LOGS_DIR.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not log_files:
        return "No log files found. Start the engine to generate logs."

    try:
        lines = log_files[0].read_text(encoding="utf-8", errors="replace").splitlines()
        recent = lines[-max_lines:] if len(lines) > max_lines else lines
        return "\n".join(recent)
    except OSError:
        return "Error reading log file."


# ===========================
# Dashboard Layout
# ===========================

def render_header() -> None:
    """Render the main header banner."""
    st.markdown("""
    <div class="main-header">
        <h1>🛡️ ScrapeGuard Dashboard</h1>
        <p>Automated Structural Integrity Watchdog — Real-time target health monitoring</p>
    </div>
    """, unsafe_allow_html=True)


def render_summary_cards(results: list[dict]) -> None:
    """Render the top-level summary metric cards."""
    healthy = sum(1 for r in results if r.get("status") == "HEALTHY")
    broken = sum(1 for r in results if r.get("status") == "SCHEMA_BROKEN")
    errors = sum(1 for r in results if r.get("status") == "CONNECTION_ERROR")
    total = len(results)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="status-card" style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); border-left: 5px solid #667eea;">
            <div class="count">{total}</div>
            <div class="label">Total Targets</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="status-card status-healthy">
            <div class="count">{healthy}</div>
            <div class="label">Healthy</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="status-card status-broken">
            <div class="count">{broken}</div>
            <div class="label">Schema Broken</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="status-card status-error">
            <div class="count">{errors}</div>
            <div class="label">Connection Error</div>
        </div>
        """, unsafe_allow_html=True)


def _status_badge(status: str) -> str:
    """Return an HTML badge for a given status string."""
    badges = {
        "HEALTHY": '<span class="badge badge-healthy">✅ Healthy</span>',
        "SCHEMA_BROKEN": '<span class="badge badge-broken">❌ Schema Broken</span>',
        "CONNECTION_ERROR": '<span class="badge badge-error">⚠️ Connection Error</span>',
    }
    return badges.get(status, f'<span class="badge">{status}</span>')


def render_target_results(results: list[dict]) -> None:
    """Render detailed per-target result cards."""
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    st.markdown("### 📋 Target Health Details")

    if not results:
        st.info("No results yet. Run the engine or click **Test All Targets** to begin.")
        return

    for r in results:
        status = r.get("status", "UNKNOWN")
        badge = _status_badge(status)
        name = r.get("target_name", "Unknown")
        url = r.get("url", "N/A")
        ts = r.get("timestamp", "N/A")
        errors = r.get("errors", [])
        extracted = r.get("extracted_data", {})

        # Format timestamp
        try:
            dt = datetime.fromisoformat(ts)
            ts_display = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        except (ValueError, TypeError):
            ts_display = ts

        st.markdown(f"""
        <div class="target-card" style="border-left-color: {'#38ef7d' if status == 'HEALTHY' else '#ff6b6b' if status == 'SCHEMA_BROKEN' else '#feca57'};">
            <div class="target-name">{name} {badge}</div>
            <div class="target-url">🔗 {url}</div>
            <div class="target-time">🕐 Last checked: {ts_display}</div>
        </div>
        """, unsafe_allow_html=True)

        # Expandable details
        with st.expander(f"Details — {name}", expanded=False):
            if errors:
                st.error("**Validation Errors:**")
                for err in errors:
                    st.markdown(f"- `{err}`")

            if extracted:
                st.json(extracted)
            else:
                st.caption("No extracted data available.")


def render_log_terminal() -> None:
    """Render the live log viewer terminal."""
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    st.markdown("### 🖥️ Live Log Terminal")

    logs = load_recent_logs()
    st.markdown(
        f'<div class="log-terminal">{logs}</div>',
        unsafe_allow_html=True,
    )


def render_sidebar(targets_config: list[dict]) -> None:
    """Render the sidebar with target list and controls."""
    with st.sidebar:
        st.markdown("## 🎯 Registered Targets")
        st.markdown(f"**Count:** {len(targets_config)}")
        st.markdown("---")

        for t in targets_config:
            name = t.get("name", "Unknown")
            url = t.get("url", "N/A")
            interval = t.get("schedule_minutes", "N/A")
            selectors = t.get("selectors", {})

            st.markdown(f"**{name}**")
            st.caption(f"🔗 {url}")
            st.caption(f"⏱️ Every {interval} min  |  📌 {len(selectors)} field(s)")
            st.markdown("---")

        st.markdown("## ⚙️ Settings")
        st.caption(f"📁 Results: `{RESULTS_FILE.name}`")
        st.caption(f"📂 Logs: `{LOGS_DIR}`")
        st.caption(f"🔄 Auto-refresh: {DASHBOARD_REFRESH_SECONDS}s")


# ===========================
# Main Dashboard Entry
# ===========================

def main() -> None:
    """Assemble and render the complete dashboard."""
    render_header()

    # Load current state from disk
    data = load_results()
    results = data.get("results", [])
    last_run = data.get("last_run")
    targets_config = load_targets_config()

    # Sidebar
    render_sidebar(targets_config)

    # Last run timestamp
    if last_run:
        try:
            dt = datetime.fromisoformat(last_run)
            st.caption(f"🕐 Last engine run: **{dt.strftime('%Y-%m-%d %H:%M:%S UTC')}**")
        except (ValueError, TypeError):
            st.caption(f"🕐 Last engine run: **{last_run}**")
    else:
        st.caption("🕐 No engine run recorded yet.")

    # Summary cards
    render_summary_cards(results)

    # Manual trigger button
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    col_btn, col_info = st.columns([1, 3])
    with col_btn:
        test_all = st.button(
            "🚀 Test All Targets",
            type="primary",
            use_container_width=True,
            key="btn_test_all",
        )

    if test_all:
        with st.spinner("🔄 Running scrape & validation cycle... Please wait."):
            # Both app.py and main_engine.py live in project root
            from main_engine import run_full_cycle
            cycle_results = run_full_cycle()

        st.success(
            f"✅ Cycle complete — "
            f"{sum(1 for r in cycle_results if r.status == 'HEALTHY')} healthy, "
            f"{sum(1 for r in cycle_results if r.status == 'SCHEMA_BROKEN')} broken, "
            f"{sum(1 for r in cycle_results if r.status == 'CONNECTION_ERROR')} errors"
        )
        # Rerun to refresh displayed data
        st.rerun()

    # Target details
    render_target_results(results)

    # Log terminal
    render_log_terminal()

    # Auto-refresh
    st.markdown(
        f"<meta http-equiv='refresh' content='{DASHBOARD_REFRESH_SECONDS}'>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
