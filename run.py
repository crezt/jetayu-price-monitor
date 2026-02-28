#!/usr/bin/env python3
"""
Jetayu Gadgets — Competitor Price Monitor
Run with: python run.py
"""

import shutil
import subprocess
import sys
import os
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT, "data")
SNAPSHOTS_DIR = os.path.join(DATA_DIR, "snapshots")


def install_deps():
    req_file = os.path.join(ROOT, "requirements.txt")
    print("[*] Checking / installing dependencies …")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "--user", "-q", "-r", req_file],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    print("[✓] Dependencies ready.\n")


def ensure_dirs():
    os.makedirs(SNAPSHOTS_DIR, exist_ok=True)


def main():
    t0 = time.time()
    print("=" * 60)
    print("  Jetayu Gadgets — Competitor Price Monitor")
    print("=" * 60, "\n")

    # 1. deps
    install_deps()
    ensure_dirs()

    # 2. scrape
    from scraper import run_all_scrapers
    snapshot_path = run_all_scrapers(SNAPSHOTS_DIR)

    # 3. compare
    from compare import compare_snapshots
    changes = compare_snapshots(SNAPSHOTS_DIR)

    # 4. dashboard
    from dashboard import generate_dashboard
    dash_path = os.path.join(DATA_DIR, "dashboard.html")
    generate_dashboard(snapshot_path, changes, dash_path)

    # Copy to docs/ for GitHub Pages
    docs_dir = os.path.join(ROOT, "docs")
    os.makedirs(docs_dir, exist_ok=True)
    shutil.copy2(dash_path, os.path.join(docs_dir, "index.html"))

    elapsed = time.time() - t0
    print(f"\n{'=' * 60}")
    print(f"  Done in {elapsed:.1f}s")
    print(f"  Dashboard → file://{dash_path}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
