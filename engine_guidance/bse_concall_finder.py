"""
Concall Transcript Finder

Discovers and downloads earnings call transcripts for NSE-listed companies.
Primary source: screener.in (aggregates BSE filings with labels).
Downloads PDFs from BSE, converts to text, and stores via TranscriptCollector.

Usage:
    python -m engine_guidance.bse_concall_finder --symbol RELIANCE --dry-run
    python -m engine_guidance.bse_concall_finder --symbol TCS --quarters 4

Strategy:
    1. Scrape screener.in/company/{SYMBOL}/consolidated/
    2. Parse the #documents section, filter for "Transcript" items
    3. Extract BSE PDF URL from each transcript row
    4. Parse date from label (e.g., "Apr 2026Transcript..." → 2026-04-15)
    5. Download PDF, convert to text with pdftotext
    6. Store via engine_fundamental.transcript_collector.TranscriptCollector
"""

import logging
import os
import re
import subprocess
import tempfile
from datetime import date, datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("concall_finder")

# ── Constants ────────────────────────────────────────────────────────────
SCREENER_BASE = "https://www.screener.in"
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml",
}


def parse_label_date(label: str) -> Optional[date]:
    """
    Parse date from screener.in transcript label.
    Examples: 'Apr 2026Transcript...' → 2026-04-15
              'Jan 2025Transcript...' → 2025-01-15
              'Oct 2024Transcript...' → 2024-10-15
    """
    months = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4,
        "may": 5, "jun": 6, "jul": 7, "aug": 8,
        "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    }

    match = re.match(r"([A-Za-z]{3})\s+(\d{4})", label)
    if not match:
        return None

    month_str = match.group(1).lower()
    year = int(match.group(2))

    month = months.get(month_str)
    if not month:
        return None

    return date(year, month, 15)


def fetch_screener_documents(symbol: str) -> list[dict]:
    """
    Scrape screener.in for transcript document links.

    Returns list of dicts with 'label', 'date', 'url'.
    """
    url = f"{SCREENER_BASE}/company/{symbol.upper()}/consolidated/"
    logger.info(f"Fetching: {url}")

    try:
        resp = requests.get(url, headers=REQUEST_HEADERS, timeout=30)
        if resp.status_code != 200:
            logger.warning(f"screener.in returned {resp.status_code}")
            return []
    except Exception as e:
        logger.error(f"Failed to fetch screener.in: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    doc_section = soup.find(id="documents")

    if not doc_section:
        logger.warning(f"No #documents section found for {symbol}")
        return []

    # Find all transcript items
    transcripts = []
    items = doc_section.find_all(["li", "tr", "div"])

    for item in items:
        text = item.get_text(strip=True)
        if "Transcript" not in text or len(text) > 300:
            continue

        # Find BSE PDF link
        for link in item.find_all("a", href=True):
            href = link["href"]
            if "bseindia.com" not in href:
                continue
            if not (".pdf" in href or "AnnPdfOpen" in href or "AttachHis" in href):
                continue

            doc_date = parse_label_date(text)
            transcripts.append({
                "label": text[:100],
                "date": doc_date,
                "url": href,
            })
            break  # One URL per transcript row

    logger.info(f"  Found {len(transcripts)} transcripts for {symbol}")
    return transcripts


def pdf_to_text(pdf_path: str) -> Optional[str]:
    """Extract text from PDF using markitdown (Markdown output)."""
    try:
        from markitdown import MarkItDown
        md = MarkItDown()
        result = md.convert(pdf_path)
        text = result.text_content

        if text and len(text.strip()) > 200:
            logger.info(f"  markitdown: {len(text)} chars extracted (Markdown)")
            return text
    except ImportError:
        logger.warning("markitdown not installed — falling back to pdftotext")
        try:
            subprocess.run(
                ["pdftotext", "-layout", pdf_path, pdf_path + ".txt"],
                check=True, capture_output=True, timeout=30,
            )
            with open(pdf_path + ".txt", "r", errors="replace") as f:
                text = f.read()
            os.unlink(pdf_path + ".txt")
            if len(text.strip()) > 200:
                logger.info(f"  pdftotext fallback: {len(text)} chars extracted")
                return text
        except Exception as e:
            logger.debug(f"  pdftotext fallback failed: {e}")
    except Exception as e:
        logger.debug(f"  markitdown failed: {e}")

    return None


def download_and_extract(pdf_url: str) -> Optional[str]:
    """Download PDF from BSE and extract text."""
    try:
        resp = requests.get(
            pdf_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=60
        )
        if resp.status_code != 200 or len(resp.content) < 1000:
            logger.warning(f"  Download failed: HTTP {resp.status_code}, {len(resp.content)} bytes")
            return None
    except Exception as e:
        logger.error(f"  Download error: {e}")
        return None

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(resp.content)
        pdf_path = f.name

    text = pdf_to_text(pdf_path)
    os.unlink(pdf_path)
    return text


def find_and_ingest_concalls(
    symbol: str,
    quarters_back: int = 8,
    dry_run: bool = False,
) -> int:
    """
    Main entry point: find transcript PDFs for a symbol and ingest them.

    Args:
        symbol: NSE ticker (e.g. 'RELIANCE')
        quarters_back: how many quarters of history to process
        dry_run: if True, download and extract but don't store in DB

    Returns:
        Number of transcripts successfully processed
    """
    symbol = symbol.upper()
    logger.info(f"=== Concall Finder: {symbol} ===")

    # 1. Scrape screener.in for transcript links
    transcripts = fetch_screener_documents(symbol)
    if not transcripts:
        logger.warning(f"No transcripts found for {symbol}")
        return 0

    # 2. Process each transcript (most recent first, up to quarters_back * 2)
    ingested = 0
    for doc in transcripts[: quarters_back * 2]:
        label = doc["label"]
        doc_date = doc["date"] or date.today()
        pdf_url = doc["url"]

        logger.info(f"  [{label}] → downloading...")

        # Download and extract
        text = download_and_extract(pdf_url)
        if not text:
            logger.warning(f"    Text extraction failed")
            continue

        logger.info(
            f"    {len(text)} chars, preview: {text[:100].strip()}"
        )

        if dry_run:
            logger.info(f"    [DRY RUN] Would store with date {doc_date}")
            ingested += 1
            continue

        # Store via existing TranscriptCollector
        try:
            from engine_fundamental.transcript_collector import (
                TranscriptCollector,
            )

            collector = TranscriptCollector()
            collector.store_transcript(
                symbol=symbol,
                date=doc_date,
                text=text,
                source_url=pdf_url,
            )
            logger.info(f"    Stored in aae_transcripts")
            ingested += 1
        except Exception as e:
            logger.error(f"    Storage error: {e}")

    logger.info(f"=== {symbol}: {ingested}/{len(transcripts)} ingested ===")
    return ingested


# ── CLI ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Concall Transcript Finder (screener.in → BSE PDF)"
    )
    parser.add_argument(
        "--symbol", "-s", required=True, help="NSE ticker symbol"
    )
    parser.add_argument(
        "--quarters", "-q", type=int, default=8,
        help="How many quarters of transcripts to process (default: 8)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Download and extract but don't store in DB"
    )

    args = parser.parse_args()

    count = find_and_ingest_concalls(
        symbol=args.symbol,
        quarters_back=args.quarters,
        dry_run=args.dry_run,
    )

    print(f"\nDone. {count} transcripts processed for {args.symbol}.")
