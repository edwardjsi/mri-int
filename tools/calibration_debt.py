#!/usr/bin/env python3
"""Calibration Debt counter.

Reads config/calibration_registry.yaml and counts:
  - Total assumptions
  - Validated assumptions
  - Hypothesis (unvalidated) → DEBT

Per Decision 101 expert feedback: YAML should hold runtime config;
calibration_registry.yaml tracks validation status; this tool computes
the running debt.

Usage:
    venv/bin/python tools/calibration_debt.py
    venv/bin/python tools/calibration_debt.py --json  # machine-readable
    venv/bin/python tools/calibration_debt.py --exit-nonzero  # CI gate

Returns exit 0 if --exit-nonzero not passed.
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import yaml

REGISTRY_PATH = Path(__file__).parent.parent / "config" / "calibration_registry.yaml"


def load_registry(path: Path = REGISTRY_PATH) -> dict:
    if not path.exists():
        print(f"ERROR: registry not found at {path}", file=sys.stderr)
        sys.exit(2)
    with open(path) as f:
        return yaml.safe_load(f)


def compute_debt(registry: dict) -> dict:
    """Aggregate status counts and list entries."""
    by_status: Counter = Counter()
    entries = []
    for name, entry in registry.items():
        if not isinstance(entry, dict) or "status" not in entry:
            # Skip malformed entries (e.g., comments-only blocks)
            continue
        status = entry.get("status", "unknown")
        by_status[status] += 1
        entries.append({
            "name": name,
            "status": status,
            "value": entry.get("value"),
            "rationale": entry.get("rationale", ""),
            "introduced": entry.get("introduced"),
            "last_reviewed": entry.get("last_reviewed"),
            "validated_after": entry.get("validated_after"),
            "journal_entry": entry.get("journal_entry"),
        })

    total = sum(by_status.values())
    validated = by_status.get("validated", 0)
    debt = total - validated
    return {
        "total": total,
        "validated": validated,
        "debt": debt,
        "by_status": dict(by_status),
        "entries": entries,
    }


def print_human(report: dict) -> None:
    print(f"Calibration Debt Report")
    print(f"{'=' * 50}")
    print(f"Total assumptions: {report['total']}")
    print(f"  Validated:       {report['validated']}")
    print(f"  Deprecated:      {report['by_status'].get('deprecated', 0)}")
    print(f"  Hypothesis:      {report['by_status'].get('hypothesis', 0)}")
    print(f"")
    print(f"DEBT: {report['debt']}")
    print(f"")
    if report["debt"] > 0:
        print("Unvalidated entries (will appear in Calibration.md once measured):")
        print()
        for e in report["entries"]:
            if e["status"] == "hypothesis":
                print(f"  • {e['name']}")
                print(f"      value:        {e['value']}")
                print(f"      introduced:   {e['introduced']}")
                print(f"      rationale:    {e['rationale']}")
                print(f"      journal:      {e['journal_entry'] or '(none yet)'}")
                print()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--json", action="store_true", help="emit JSON instead of human-readable")
    p.add_argument("--registry", type=Path, default=REGISTRY_PATH,
                   help="path to calibration_registry.yaml")
    p.add_argument("--exit-nonzero", action="store_true",
                   help="exit 1 if debt > 0 (useful for CI)")
    args = p.parse_args()

    registry = load_registry(args.registry)
    report = compute_debt(registry)

    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print_human(report)

    if args.exit_nonzero and report["debt"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
