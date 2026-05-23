"""AAE Sourcing and NLP Agent.

Converts unstructured documents into structured, finance-aware event objects.
Classifies documents, extracts entities, and detects semantic triggers.

This agent is designed to work with GPT-4o-mini for NLP tasks, but the
scaffolding and deterministic classification runs without LLM calls.

Usage (standalone test):
    python engine_core/aae_sourcing_agent.py --symbol RELIANCE --doc-id 1
"""

from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any

from engine_core.db import get_connection, fetch_df

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("aae_sourcing")

# ---------------------------------------------------------------------------
# Semantic trigger patterns — keyword-based detection (deterministic fallback)
# ---------------------------------------------------------------------------

TRIGGER_PATTERNS: dict[str, list[str]] = {
    "BROWNFIELD_EXPANSION": [
        "capacity expansion", "brownfield", "expanding capacity",
        "new production line", "debottlenecking", "capacity addition",
    ],
    "GREENFIELD_EXPANSION": [
        "greenfield", "new plant", "new facility", "new manufacturing unit",
        "greenfield project", "new factory",
    ],
    "BACKWARD_INTEGRATION": [
        "backward integration", "backward integrated", "in-house", "captive",
        "own sourcing", "raw material security",
    ],
    "FORWARD_INTEGRATION": [
        "forward integration", "direct-to-consumer", "D2C", "own retail",
        "branded retail", "company-operated stores",
    ],
    "NEW_PRODUCT_SEGMENT": [
        "new product", "new segment", "product launch", "new category",
        "entering the", "foray into", "adjacent category",
    ],
    "GEOGRAPHIC_EXPANSION": [
        "new geography", "international expansion", "new market",
        "export market", "overseas", "global expansion", "new country",
    ],
    "MOAT_STRENGTHENING": [
        "patent", "proprietary", "market share gain", "brand strengthening",
        "technology leadership", "R&D breakthrough", "network effect",
    ],
    "CAPACITY_ADDITION": [
        "capacity", "throughput", "volumes increased", "production increased",
        "output expansion", "scale up",
    ],
    "COST_OPTIMIZATION": [
        "cost reduction", "cost optimization", "efficiency improvement",
        "automation", "digital transformation", "operational efficiency",
    ],
    "MANAGEMENT_CHANGE": [
        "new CEO", "new CFO", "management change", "leadership change",
        "appointed as", "resignation of", "board restructuring",
    ],
    "GOVERNANCE_RED_FLAG": [
        "auditor resignation", "qualified opinion", "SEBI notice",
        "regulatory action", "income tax raid", "ED investigation",
    ],
    "CAPITAL_ALLOCATION": [
        "share buyback", "dividend increase", "bonus issue",
        "capital return", "special dividend", "demerger",
    ],
}

# Document type classification by keyword
DOC_TYPE_KEYWORDS: dict[str, list[str]] = {
    "TRANSCRIPT":    ["conference call", "earnings call", "Q&A", "analyst meet", "investor call"],
    "FILING":        ["annual report", "quarterly report", "filing", "balance sheet", "profit & loss"],
    "PRESENTATION":  ["investor presentation", "corporate presentation", "earnings presentation", "deck"],
    "ANNOUNCEMENT":  ["press release", "announcement", "notice", "disclosure", "intimation"],
    "REPORT":        ["research report", "industry report", "sector report", "analysis"],
}


def classify_document(text: str, title: str = "") -> str:
    """Classify document type from text content using keyword matching."""
    combined = (title + " " + text[:2000]).lower()
    scores = {}
    for doc_type, keywords in DOC_TYPE_KEYWORDS.items():
        scores[doc_type] = sum(1 for kw in keywords if kw.lower() in combined)

    best = max(scores, key=scores.get)
    if scores[best] > 0:
        return best
    return "FILING"  # default


def detect_triggers(text: str) -> list[dict[str, Any]]:
    """Detect semantic triggers from document text using keyword matching.

    Returns a list of trigger dicts with type, confidence, and evidence snippet.
    """
    text_lower = text.lower()
    triggers = []

    for trigger_type, keywords in TRIGGER_PATTERNS.items():
        for kw in keywords:
            idx = text_lower.find(kw.lower())
            if idx >= 0:
                # Extract context snippet (~150 chars around the match)
                start = max(0, idx - 75)
                end = min(len(text), idx + len(kw) + 75)
                snippet = text[start:end].strip()

                triggers.append({
                    "trigger_type": trigger_type,
                    "keyword_matched": kw,
                    "confidence": 0.7,  # keyword match = moderate confidence
                    "snippet": snippet,
                })
                break  # one match per trigger type

    return triggers


def extract_entities(text: str) -> dict[str, list[str]]:
    """Extract named entities using simple pattern matching.

    Returns dict with keys: companies, projects, geographies, products.
    """
    entities: dict[str, list[str]] = {"companies": [], "projects": [], "geographies": [], "products": []}
    text_lower = text.lower()

    # Simple geography extraction
    countries = ["india", "usa", "united states", "europe", "uk", "germany", "japan",
                 "china", "uae", "singapore", "australia", "bangladesh", "sri lanka"]
    for country in countries:
        if country in text_lower:
            entities["geographies"].append(country.title())

    return entities


class SourcingAgent:
    """AAE Sourcing and NLP Agent.

    Processes raw documents into structured event objects with:
    - Document classification
    - Entity extraction
    - Semantic trigger detection
    - Management claim summarization

    For production, the summarization and deep extraction use GPT-4o-mini.
    The deterministic fallback uses keyword matching.
    """

    def __init__(self, symbol: str):
        self.symbol = symbol.upper()

    def process_document(self, doc_id: int) -> dict[str, Any]:
        """Process one document: classify, extract triggers, create events."""
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, symbol, doc_type, title, doc_date, raw_text
                    FROM public.aae_documents
                    WHERE id = %s AND symbol = %s
                    """,
                    (doc_id, self.symbol),
                )
                doc = cur.fetchone()
                if not doc:
                    return {"error": f"Document {doc_id} not found for {self.symbol}"}

                doc_dict = dict(doc)
                text = doc_dict["raw_text"] or ""

                # Classify (override if stored type is generic)
                detected_type = classify_document(text, doc_dict.get("title", ""))
                if doc_dict["doc_type"] not in ("FILING", "TRANSCRIPT", "PRESENTATION", "ANNOUNCEMENT", "REPORT"):
                    doc_dict["doc_type"] = detected_type

                # Detect triggers
                triggers = detect_triggers(text)

                # Extract entities
                entities = extract_entities(text)

                # Create event objects from triggers
                events_created = []
                for trigger in triggers:
                    cur.execute(
                        """
                        INSERT INTO public.aae_events
                            (symbol, event_type, event_subtype, title, description, confidence, event_date, source_doc_id, metadata)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                        RETURNING id
                        """,
                        (
                            self.symbol,
                            trigger["trigger_type"],
                            doc_dict["doc_type"],
                            f"{trigger['trigger_type']} detected in {doc_dict.get('title', 'document')}",
                            trigger["snippet"],
                            trigger["confidence"],
                            doc_dict["doc_date"],
                            doc_id,
                            json.dumps({"keyword": trigger["keyword_matched"], "entities": entities}),
                        ),
                    )
                    event_row = cur.fetchone()
                    if event_row:
                        events_created.append({
                            "event_id": event_row["id"],
                            "event_type": trigger["trigger_type"],
                            "confidence": trigger["confidence"],
                        })

                conn.commit()

                return {
                    "document_id": doc_id,
                    "symbol": self.symbol,
                    "doc_type": doc_dict["doc_type"],
                    "doc_date": str(doc_dict["doc_date"]),
                    "triggers_detected": len(triggers),
                    "events_created": len(events_created),
                    "trigger_types": [t["trigger_type"] for t in triggers],
                    "entities": entities,
                }

        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def process_latest_documents(self, limit: int = 5) -> list[dict]:
        """Process the N most recent unprocessed documents for this symbol."""
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT d.id
                    FROM public.aae_documents d
                    WHERE d.symbol = %s
                      AND d.id NOT IN (
                          SELECT DISTINCT source_doc_id FROM public.aae_events WHERE source_doc_id IS NOT NULL
                      )
                    ORDER BY d.doc_date DESC
                    LIMIT %s
                    """,
                    (self.symbol, limit),
                )
                doc_ids = [row[0] for row in cur.fetchall()]

            results = []
            for doc_id in doc_ids:
                result = self.process_document(doc_id)
                results.append(result)

            return results
        finally:
            conn.close()


def main() -> None:
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="AAE Sourcing Agent")
    parser.add_argument("--symbol", required=True, help="Ticker symbol")
    parser.add_argument("--doc-id", type=int, help="Process specific document ID")
    parser.add_argument("--latest", type=int, default=0, help="Process N latest unprocessed documents")
    args = parser.parse_args()

    agent = SourcingAgent(args.symbol)

    if args.doc_id:
        result = agent.process_document(args.doc_id)
        print(json.dumps(result, indent=2, default=str))
    elif args.latest:
        results = agent.process_latest_documents(args.latest)
        print(json.dumps(results, indent=2, default=str))
    else:
        print("Specify --doc-id or --latest N")
        sys.exit(1)


if __name__ == "__main__":
    main()
