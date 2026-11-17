#!/usr/bin/env python3
"""Daily AUD exchange-rate snapshot (pilot for GitHub Actions).

Fetches AUD rates from the free ExchangeRate-API open endpoint (no key),
appends one row per day to data/fx-history.csv and refreshes
data/fx-latest.json. Public data only.
"""
import csv
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone

API = "https://open.er-api.com/v6/latest/AUD"


def fetch_json(url: str) -> dict:
    """Fetch JSON via curl when available (proxy-friendly), else urllib."""
    if shutil.which("curl"):
        out = subprocess.run(
            ["curl", "-fsS", "--max-time", "30", "-A", "fx-pilot/1.0", url],
            capture_output=True, text=True, check=True,
        )
        return json.loads(out.stdout)
    req = urllib.request.Request(url, headers={"User-Agent": "fx-pilot/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)
CURRENCIES = ["USD", "CNY", "GBP", "NZD", "EUR", "JPY"]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(ROOT, "data", "fx-history.csv")
JSON_PATH = os.path.join(ROOT, "data", "fx-latest.json")


def main() -> int:
    payload = fetch_json(API)
    if payload.get("result") != "success":
        print(f"API did not return success: {payload.get('result')}", file=sys.stderr)
        return 1
    rates_all = payload["rates"]
    rates = {c: round(float(rates_all[c]), 6) for c in CURRENCIES}
    updated = payload.get("time_last_update_utc", "")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
    header = ["date_utc", "base"] + CURRENCIES + ["source_updated_utc"]
    rows = []
    if os.path.exists(CSV_PATH):
        with open(CSV_PATH, newline="") as f:
            rows = list(csv.reader(f))
    if not rows:
        rows = [header]
    if rows[-1][0] == today:
        print(f"Row for {today} already present, refreshing latest.json only.")
    else:
        rows.append([today, "AUD"] + [str(rates[c]) for c in CURRENCIES] + [updated])
        with open(CSV_PATH, "w", newline="") as f:
            csv.writer(f).writerows(rows)
        print(f"Appended {today}: " + ", ".join(f"{c} {rates[c]}" for c in CURRENCIES))

    latest = {
        "date_utc": today,
        "base": "AUD",
        "rates": rates,
        "source": "open.er-api.com (ExchangeRate-API)",
        "source_updated_utc": updated,
    }
    with open(JSON_PATH, "w") as f:
        json.dump(latest, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
