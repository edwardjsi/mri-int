"""
Phase A1 of docs/INITIATIVE_DATA_RICHNESS_2026-06-19.md.

Audit which Expansion Lens universe symbols lack AAE rows, QIF rows, or both.
Output: a markdown table on stdout that becomes the work list for Phases A2
(AAE backfill) and A3 (QIF backfill).

Universe source: perx_pe_scores (the 149 symbols that the Expansion Lens
already scores). Future iterations can swap in universe_112co (192) or
stock_sectors (537) for broader coverage.

Outputs:
- Summary table: coverage by engine (AAE / QIF)
- Detailed list: each uncovered symbol with both its PE score and what it lacks
- Work-list CSVs: missing_aae.csv + missing_qif.csv (consumable by A2/A3 scripts)

Usage:
    python scripts/audit_universe_data_coverage.py
    python scripts/audit_universe_data_coverage.py --out-dir docs/data_richness_audit
"""

import argparse
import csv
import logging
import os
from datetime import datetime

from engine_core.db import get_connection

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def audit(universe_table: str = "perx_pe_scores"):
    """Run the audit and return summary + detail rows."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(f"""
            SELECT
                pe.symbol,
                pe.pe_score,
                (aae.symbol IS NOT NULL) AS has_aae,
                (qif.symbol IS NOT NULL) AS has_qif
            FROM {universe_table} pe
            LEFT JOIN (SELECT DISTINCT symbol FROM aae_results_snapshot) aae USING (symbol)
            LEFT JOIN (
                SELECT DISTINCT symbol FROM quality_verdicts
                WHERE agent_details IS NOT NULL AND agent_details != '{{}}'::jsonb
            ) qif USING (symbol)
            ORDER BY pe.pe_score DESC NULLS LAST, pe.symbol ASC
        """)
        rows = [dict(r) for r in cur.fetchall()]
        return rows
    finally:
        conn.close()


def summarize(rows):
    total = len(rows)
    with_aae = sum(1 for r in rows if r["has_aae"])
    with_qif = sum(1 for r in rows if r["has_qif"])
    with_both = sum(1 for r in rows if r["has_aae"] and r["has_qif"])
    without_aae = [r for r in rows if not r["has_aae"]]
    without_qif = [r for r in rows if not r["has_qif"]]
    missing_either = [r for r in rows if not r["has_aae"] or not r["has_qif"]]
    return {
        "total": total,
        "with_aae": with_aae,
        "with_qif": with_qif,
        "with_both": with_both,
        "without_aae": without_aae,
        "without_qif": without_qif,
        "missing_either": missing_either,
    }


def render_markdown(rows, summary) -> str:
    lines = []
    lines.append(f"# Phase A1 — Universe Data Coverage Audit")
    lines.append("")
    lines.append(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"Universe source: `perx_pe_scores` (149 Expansion Lens symbols)")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"| Metric | Count |")
    lines.append(f"|---|---|")
    lines.append(f"| Total PE universe symbols | {summary['total']} |")
    lines.append(f"| With AAE rows | {summary['with_aae']} ({summary['with_aae']/summary['total']*100:.1f}%) |")
    lines.append(f"| With QIF rows (populated agent_details) | {summary['with_qif']} ({summary['with_qif']/summary['total']*100:.1f}%) |")
    lines.append(f"| With BOTH engines | {summary['with_both']} ({summary['with_both']/summary['total']*100:.1f}%) |")
    lines.append(f"| **Missing AAE (Phase A2 target)** | **{len(summary['without_aae'])}** |")
    lines.append(f"| **Missing QIF (Phase A3 target)** | **{len(summary['without_qif'])}** |")
    lines.append(f"| **Missing either** | **{len(summary['missing_either'])}** |")
    lines.append("")
    lines.append("## Top-15 PE-ranked symbols — coverage gap check")
    lines.append("")
    lines.append("| Rank | Symbol | PE Score | AAE | QIF |")
    lines.append("|---|---|---|---|---|")
    for i, r in enumerate(rows[:15], 1):
        aae_mark = "✅" if r["has_aae"] else "❌"
        qif_mark = "✅" if r["has_qif"] else "❌"
        lines.append(f"| {i} | {r['symbol']} | {r['pe_score']:.1f} | {aae_mark} | {qif_mark} |")
    lines.append("")
    lines.append("## All symbols missing AAE (sorted by PE score desc)")
    lines.append("")
    lines.append(f"{len(summary['without_aae'])} symbols — these are the Phase A2 backfill work list.")
    lines.append("")
    lines.append("| Symbol | PE Score | QIF? |")
    lines.append("|---|---|---|")
    for r in summary["without_aae"]:
        qif_mark = "✅" if r["has_qif"] else "❌"
        lines.append(f"| {r['symbol']} | {r['pe_score']:.1f} | {qif_mark} |")
    lines.append("")
    lines.append("## All symbols missing QIF (sorted by PE score desc)")
    lines.append("")
    lines.append(f"{len(summary['without_qif'])} symbols — these are the Phase A3 backfill work list.")
    lines.append("")
    lines.append("| Symbol | PE Score | AAE? |")
    lines.append("|---|---|---|")
    for r in summary["without_qif"]:
        aae_mark = "✅" if r["has_aae"] else "❌"
        lines.append(f"| {r['symbol']} | {r['pe_score']:.1f} | {aae_mark} |")
    lines.append("")
    return "\n".join(lines)


def write_worklist_csvs(rows, out_dir):
    """Write missing_aae.csv + missing_qif.csv for the A2/A3 scripts to consume."""
    os.makedirs(out_dir, exist_ok=True)
    for filename, key in [("missing_aae.csv", "without_aae"), ("missing_qif.csv", "without_qif")]:
        path = os.path.join(out_dir, filename)
        summary = summarize(rows)
        symbols = summary[key]
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["symbol", "pe_score", "has_aae", "has_qif"])
            for r in symbols:
                w.writerow([r["symbol"], r["pe_score"], r["has_aae"], r["has_qif"]])
        logger.info(f"Wrote {len(symbols)} rows to {path}")


def main():
    parser = argparse.ArgumentParser(description="Phase A1: audit AAE/QIF coverage for PE universe")
    parser.add_argument("--universe-table", default="perx_pe_scores",
                        help="Table to use as universe source (default: perx_pe_scores)")
    parser.add_argument("--out-dir", default=None,
                        help="If set, write audit.md + missing_*.csv to this directory")
    args = parser.parse_args()

    logger.info(f"Auditing universe from {args.universe_table}")
    rows = audit(universe_table=args.universe_table)
    summary = summarize(rows)
    md = render_markdown(rows, summary)

    print(md)

    if args.out_dir:
        os.makedirs(args.out_dir, exist_ok=True)
        md_path = os.path.join(args.out_dir, "audit.md")
        with open(md_path, "w") as f:
            f.write(md)
        logger.info(f"Wrote markdown audit to {md_path}")
        write_worklist_csvs(rows, args.out_dir)


if __name__ == "__main__":
    main()
