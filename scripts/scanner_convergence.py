import os
import sys
import requests
from collections import defaultdict

# We'll just call our own API endpoints locally to avoid complex import dependencies
# Assuming backend runs on 8000
API_BASE = "http://localhost:8000/api"
V1_BASE = "http://localhost:8000/api/v1"

def fetch_signals():
    counts = defaultdict(lambda: {"count": 0, "signals": []})
    
    def add_to_counts(symbol, signal_name):
        if symbol and signal_name not in counts[symbol]["signals"]:
            counts[symbol]["count"] += 1
            counts[symbol]["signals"].append(signal_name)

    # 1. Shadow Momentum (Assuming /api/signals/shadow exists, or we skip if it errors)
    try:
        r = requests.get(f"{API_BASE}/signals/shadow", timeout=5)
        if r.status_code == 200:
            for item in r.json().get("stocks", []):
                add_to_counts(item.get("symbol"), "Shadow Momentum")
    except Exception as e:
        print(f"Shadow Momentum err: {e}")

    # 2. 112 CO
    try:
        r = requests.get(f"{API_BASE}/112co/breakouts", timeout=5)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list):
                for item in data:
                    add_to_counts(item.get("symbol"), "112 CO")
    except Exception as e:
        print(f"112 CO err: {e}")

    # 3. Darvas
    try:
        r = requests.get(f"{V1_BASE}/screener/darvas", timeout=5)
        if r.status_code == 200:
            for item in r.json().get("results", []):
                add_to_counts(item.get("symbol"), "Darvas Screener")
    except Exception as e:
        print(f"Darvas err: {e}")

    # 4. Breakout Radar
    try:
        r = requests.get(f"{API_BASE}/breakout/radar", timeout=5)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list):
                for item in data:
                    add_to_counts(item.get("symbol"), "Breakout Radar")
    except Exception as e:
        print(f"Radar err: {e}")

    # 5. Pre-Breakout
    try:
        r = requests.get(f"{V1_BASE}/screener/pre-breakout", timeout=5)
        if r.status_code == 200:
            for item in r.json().get("results", []):
                add_to_counts(item.get("symbol"), "Pre-Breakout")
    except Exception as e:
        print(f"Pre-Breakout err: {e}")

    results = []
    for sym, data in counts.items():
        if data["count"] >= 3:
            results.append({
                "symbol": sym,
                "count": data["count"],
                "signals": data["signals"]
            })

    results.sort(key=lambda x: (-x["count"], x["symbol"]))

    return {
        "scan_name": "Convergence Signal",
        "total_scanned": len(counts),
        "convergence_count": len(results),
        "results": results
    }
