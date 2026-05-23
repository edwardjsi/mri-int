#!/usr/bin/env python3
"""Manual document ingestion for AAE event-driven pipeline.

Ingests filings, transcripts, presentations, and announcements into the
AAE document/event tables with chunking for later AI retrieval.

Usage:
    python scripts/ingest_aae_document.py --symbol RELIANCE --type TRANSCRIPT --file transcript.txt --date 2025-03-15
    python scripts/ingest_aae_document.py --symbol TCS --type FILING --file q4_results.pdf --date 2025-03-31 --year 2025 --quarter 4
    python scripts/ingest_aae_document.py --batch data/aae_doc_batch.csv
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
import textwrap
from datetime import date, datetime
from pathlib import Path

from engine_core.db import get_connection
from api.schema import ensure_aae_event_tables

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ingest_aae_doc")

VALID_DOC_TYPES = {"FILING", "TRANSCRIPT", "PRESENTATION", "ANNOUNCEMENT", "REPORT"}
CHUNK_SIZE_CHARS = 2000  # roughly 500 tokens


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE_CHARS) -> list[str]:
    """Split text into overlapping chunks of roughly chunk_size characters."""
    if not text:
        return []
    chunks = []
    for i, start in enumerate(range(0, len(text), chunk_size // 2)):
        chunk = text[start:start + chunk_size]
        if not chunk.strip():
            continue
        chunks.append(chunk.strip())
        if start + chunk_size >= len(text):
            break
    return chunks


def ingest_document(
    symbol: str,
    doc_type: str,
    doc_date: date,
    text: str,
    *,
    title: str | None = None,
    source_url: str | None = None,
    fiscal_year: int | None = None,
    fiscal_quarter: int | None = None,
) -> dict:
    """Ingest one document with chunking. Returns summary dict."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            ensure_aae_event_tables(cur)

            # Insert document
            cur.execute(
                """
                INSERT INTO public.aae_documents
                    (symbol, doc_type, source_url, title, doc_date, fiscal_year, fiscal_quarter, raw_text)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (symbol, doc_type, doc_date, title) DO UPDATE SET
                    raw_text    = EXCLUDED.raw_text,
                    source_url  = EXCLUDED.source_url,
                    processed_at = NOW()
                RETURNING id, (xmax = 0) AS is_insert
                """,
                (symbol.upper(), doc_type, source_url, title, doc_date, fiscal_year, fiscal_quarter, text),
            )
            doc_row = cur.fetchone()
            doc_id = doc_row["id"]
            is_new = doc_row["is_insert"]

            # Chunk and store
            chunks = chunk_text(text)
            chunk_inserted = 0
            if chunks:
                for i, chunk in enumerate(chunks):
                    cur.execute(
                        """
                        INSERT INTO public.aae_document_chunks (document_id, chunk_index, chunk_text, token_count)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (document_id, chunk_index) DO UPDATE SET
                            chunk_text = EXCLUDED.chunk_text,
                            token_count = EXCLUDED.token_count
                        """,
                        (doc_id, i, chunk, len(chunk.split())),
                    )
                    chunk_inserted += 1

            conn.commit()

            return {
                "document_id": doc_id,
                "is_new": is_new,
                "chunks_created": chunk_inserted,
                "symbol": symbol.upper(),
                "doc_type": doc_type,
            }

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def ingest_from_file(
    symbol: str,
    doc_type: str,
    doc_date: date,
    file_path: Path,
    **kwargs,
) -> dict:
    """Ingest a document from a text file."""
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    text = file_path.read_text(encoding="utf-8", errors="replace")
    return ingest_document(symbol, doc_type, doc_date, text, **kwargs)


def ingest_batch(batch_csv: Path) -> list[dict]:
    """Ingest multiple documents from a batch CSV.

    CSV columns: symbol, doc_type, doc_date, file_path, title, source_url, fiscal_year, fiscal_quarter
    """
    results = []
    with open(batch_csv, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            symbol = row["symbol"].strip().upper()
            doc_type = row["doc_type"].strip().upper()
            doc_date = datetime.strptime(row["doc_date"].strip(), "%Y-%m-%d").date()
            file_path = Path(row["file_path"].strip())
            title = row.get("title", "").strip() or None
            source_url = row.get("source_url", "").strip() or None
            fy = int(row["fiscal_year"]) if row.get("fiscal_year", "").strip() else None
            fq = int(row["fiscal_quarter"]) if row.get("fiscal_quarter", "").strip() else None

            logger.info(f"Ingesting {symbol} {doc_type} ({doc_date})...")
            result = ingest_from_file(
                symbol, doc_type, doc_date, file_path,
                title=title, source_url=source_url,
                fiscal_year=fy, fiscal_quarter=fq,
            )
            results.append(result)

    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest AAE documents")
    parser.add_argument("--symbol", help="Ticker symbol")
    parser.add_argument("--type", dest="doc_type", choices=sorted(VALID_DOC_TYPES), help="Document type")
    parser.add_argument("--file", dest="file_path", help="Path to text file")
    parser.add_argument("--text", help="Inline text to ingest")
    parser.add_argument("--date", dest="doc_date", help="Document date (YYYY-MM-DD)")
    parser.add_argument("--title", help="Document title")
    parser.add_argument("--source-url", help="Source URL")
    parser.add_argument("--year", type=int, dest="fiscal_year", help="Fiscal year")
    parser.add_argument("--quarter", type=int, dest="fiscal_quarter", help="Fiscal quarter")
    parser.add_argument("--batch", help="Path to batch CSV")
    args = parser.parse_args(argv or sys.argv[1:])

    if args.batch:
        results = ingest_batch(Path(args.batch))
        print(f"\nBatch complete: {len(results)} documents")
        for r in results:
            status = "NEW" if r["is_new"] else "UPDATED"
            print(f"  {r['symbol']} {r['doc_type']} → [{status}] doc_id={r['document_id']} ({r['chunks_created']} chunks)")
        return 0

    if not args.symbol or not args.doc_type or not args.doc_date:
        parser.error("--symbol, --type, and --date are required for single document ingestion")

    doc_date = datetime.strptime(args.doc_date, "%Y-%m-%d").date()

    if args.file_path:
        result = ingest_from_file(
            args.symbol, args.doc_type, doc_date, Path(args.file_path),
            title=args.title, source_url=args.source_url,
            fiscal_year=args.fiscal_year, fiscal_quarter=args.fiscal_quarter,
        )
    elif args.text:
        result = ingest_document(
            args.symbol, args.doc_type, doc_date, args.text,
            title=args.title, source_url=args.source_url,
            fiscal_year=args.fiscal_year, fiscal_quarter=args.fiscal_quarter,
        )
    else:
        parser.error("Either --file or --text is required")

    status = "NEW" if result["is_new"] else "UPDATED"
    print(f"{result['symbol']} {result['doc_type']} → [{status}] doc_id={result['document_id']} ({result['chunks_created']} chunks)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
