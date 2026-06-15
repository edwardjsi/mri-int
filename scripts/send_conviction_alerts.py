"""
Quarterly Conviction Alert runner (Decision 097).

Detects verdict-flip companies (where current_verdict differs from
previous_verdict) and emails opted-in clients with a summary.

Usage:
    python3 scripts/send_conviction_alerts.py                # run on all flips
    python3 scripts/send_conviction_alerts.py --dry-run      # print flips, don't send
    python3 scripts/send_conviction_alerts.py --preview HTML # write preview to file
"""
import argparse
import json
import logging
import os
import sys
from datetime import date, timedelta

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("conviction_alerts")

from engine_core.db import get_connection
from engine_core.conviction_alert_email import build_conviction_alert_email_html


def fetch_flips(since_date=None):
    """Return list of dicts describing verdict flips detected in the run window."""
    if since_date is None:
        since_date = date.today() - timedelta(days=7)
    conn = get_connection()
    try:
        cur = conn.cursor()
        # Need symbol → source list. Union all three.
        cur.execute("SELECT DISTINCT UPPER(symbol) AS symbol FROM client_external_holdings")
        dt = {r["symbol"] for r in cur.fetchall()}
        cur.execute("SELECT DISTINCT UPPER(symbol) AS symbol FROM client_watchlist")
        wl = {r["symbol"] for r in cur.fetchall()}
        cur.execute("SELECT DISTINCT UPPER(symbol) AS symbol FROM universe_112co WHERE is_active=TRUE")
        co = {r["symbol"] for r in cur.fetchall()}

        cur.execute(
            """SELECT symbol, accuracy_pct, current_verdict, previous_verdict,
                      consecutive_miss_quarters, lag_score, last_verdict_flip
               FROM management_credibility_scores
               WHERE last_verdict_flip >= %s
                 AND previous_verdict IS NOT NULL
                 AND current_verdict IS DISTINCT FROM previous_verdict
               ORDER BY lag_score DESC NULLS LAST, accuracy_pct ASC""",
            (since_date,),
        )
        flips = []
        for r in cur.fetchall():
            sym = r["symbol"]
            sources = []
            if sym in dt: sources.append("digital_twin")
            if sym in wl: sources.append("watchlist")
            if sym in co: sources.append("112co")
            flips.append({
                "symbol": sym,
                "old_verdict": r["previous_verdict"],
                "new_verdict": r["current_verdict"],
                "accuracy_pct": float(r["accuracy_pct"] or 0),
                "consecutive_miss_quarters": r["consecutive_miss_quarters"] or 0,
                "lag_score": float(r["lag_score"] or 0),
                "sources": sources,
            })
        return flips
    finally:
        conn.close()


def fetch_opted_in_clients():
    """Return list of (client_id, email, client_name) for users with
    conviction_alerts_enabled = TRUE."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT c.id, c.email, COALESCE(c.name, '') AS name
               FROM public.client_alert_preferences p
               JOIN public.clients c ON c.id = p.client_id
               WHERE p.conviction_alerts_enabled = TRUE"""
        )
        return cur.fetchall()
    finally:
        conn.close()


def main():
    ap = argparse.ArgumentParser(description="ConvictionEngine verdict-flip alerter")
    ap.add_argument("--dry-run", action="store_true",
                    help="Print flips without sending email")
    ap.add_argument("--preview", metavar="PATH",
                    help="Write the HTML to this path (no email sent)")
    ap.add_argument("--since-days", type=int, default=7,
                    help="Look-back window in days (default 7)")
    args = ap.parse_args()

    since = date.today() - timedelta(days=args.since_days)
    flips = fetch_flips(since_date=since)
    logger.info(f"Found {len(flips)} verdict flips since {since}")
    if not flips:
        print("No flips in window.")
        return 0

    print("\nFlips detected:")
    for f in flips:
        print(f"  {f['symbol']:12s} {f['old_verdict']:14s} → {f['new_verdict']:14s} "
              f"acc={f['accuracy_pct']:.1f}% lag={f['consecutive_miss_quarters']}q sources={f['sources']}")

    html = build_conviction_alert_email_html(flips)

    if args.preview:
        with open(args.preview, "w") as fp:
            fp.write(html)
        print(f"\nPreview written to {args.preview}")
        return 0

    if args.dry_run:
        print("\n[DRY RUN] No emails sent.")
        return 0

    clients = fetch_opted_in_clients()
    if not clients:
        print("\nNo opted-in clients. To opt in:")
        print("  INSERT INTO client_alert_preferences (client_id, conviction_alerts_enabled)")
        print("  VALUES ('<your-client-id>', TRUE);")
        return 0

    # Send
    try:
        from engine_core.email_service import get_ses_client, send_email_custom
    except Exception as e:
        print(f"Cannot import email_service: {e}")
        print("Likely the email_service module has unrelated edits — write a preview instead.")
        with open("outputs/conviction_alert_preview.html", "w") as fp:
            fp.write(html)
        print("Wrote outputs/conviction_alert_preview.html")
        return 1

    ses = get_ses_client()
    subject = f"🚨 Conviction Alert — {len(flips)} verdict flip{'s' if len(flips) != 1 else ''} ({date.today().isoformat()})"
    sent = failed = 0
    for c in clients:
        try:
            send_email_custom(c["email"], subject, html)
            sent += 1
            logger.info(f"  Sent to {c['email']}")
        except Exception as e:
            failed += 1
            logger.error(f"  Failed for {c['email']}: {e}")
    print(f"\nDone. {sent} sent, {failed} failed.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
