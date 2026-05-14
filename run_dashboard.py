"""
ScrapeGuard — Root Dashboard Launcher.

Always run the Streamlit dashboard from the project root directory
via this script. It ensures PYTHONPATH is correctly set so that all
absolute imports (config.*, src.*) resolve properly.

Usage:
    python run_dashboard.py
"""

import subprocess
import sys
import os


def main() -> None:
    """Launch the Streamlit dashboard with correct PYTHONPATH."""
    # Set project root as PYTHONPATH for child process
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.dirname(os.path.abspath(__file__))
    # Ensure UTF-8 encoding for the child Streamlit process
    env["PYTHONUTF8"] = "1"

    cmd = [sys.executable, "-m", "streamlit", "run", "app.py"]

    print("[ScrapeGuard] Launching Dashboard...")
    print(f"   Command    : {' '.join(cmd)}")
    print(f"   PYTHONPATH : {env['PYTHONPATH']}")
    print()

    try:
        subprocess.run(cmd, env=env, check=True)
    except KeyboardInterrupt:
        print("\n[ScrapeGuard] Dashboard stopped by user.")
    except subprocess.CalledProcessError as exc:
        print(f"[ERROR] Streamlit exited with code {exc.returncode}")
        sys.exit(exc.returncode)


if __name__ == "__main__":
    main()
