"""
P2 tests: Embedded Debate (Phase 1-3).

Coverage:
- GET /api/guidance/{symbol}/debate (cache hit + miss)
- GET /api/pe-expansion/{symbol}/debate (cache hit + miss)
- get_latest_debate_for_symbol email helper (latest by generated_at)
- render_pe_expansion_email includes debate section when cached
- build_guidance_report_email_html includes debate section when cached
"""

import hashlib
import json
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from engine_debate.cache import get_latest_debate_for_symbol
from engine_core.db import ensure_pool, get_connection


def _setup_debate(symbol: str, kind: str, bear: str = "B", bull: str = "U"):
    """Insert a fresh debate row for the test symbol."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        payload = {"test": True, "symbol": symbol}
        h = hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str, ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        cur.execute(
            """INSERT INTO conviction_debates
               (symbol, context_kind, context_hash, context_payload,
                bear_text, bull_text, adjudicator, model_used)
               VALUES (%s, %s, %s, %s::jsonb, %s, %s, %s, %s)
               ON CONFLICT (symbol, context_kind, context_hash)
               DO UPDATE SET generated_at = CURRENT_TIMESTAMP,
                             bear_text = EXCLUDED.bear_text,
                             bull_text = EXCLUDED.bull_text""",
            (symbol.upper(), kind, h, json.dumps(payload), bear, bull, None, "test-model"),
        )
        conn.commit()
        return {**payload, "context_hash": h}
    finally:
        conn.close()


@pytest.fixture(autouse=True)
def ensure_test_pool():
    ensure_pool()
    yield


class TestGetLatestDebateForSymbol:
    def test_returns_latest_by_generated_at(self):
        sym = "TESTMETA"
        _setup_debate(sym, "guidance", bear="old goose", bull="old bull")
        _setup_debate(sym, "guidance", bear="new bear", bull="new bull")
        result = get_latest_debate_for_symbol(sym, "guidance")
        assert result is not None
        assert result["bear"] == "new bear"
        assert result["bull"] == "new bull"
        assert result["cached"] is True
        assert result["model_used"] == "test-model"

    def test_returns_none_when_no_debate(self):
        result = get_latest_debate_for_symbol("NO_SUCH_SYMBOL_12345", "guidance")
        assert result is None

    def test_filters_by_context_kind(self):
        sym = "TESTDUAL"
        _setup_debate(sym, "guidance", bear="guidance bear", bull="guidance bull")
        _setup_debate(sym, "pe_expansion", bear="pe bear", bull="pe bull")
        g = get_latest_debate_for_symbol(sym, "guidance")
        p = get_latest_debate_for_symbol(sym, "pe_expansion")
        assert "guidance" in g["bear"]
        assert "pe " in p["bear"]


class TestGuidanceDebateCachedEndpoint:
    def test_cache_hit_returns_cached(self):
        with patch("api.guidance.build_guidance_context") as mock_ctx:
            with patch("api.guidance.canonical_hash") as mock_hash:
                with patch("api.guidance.lookup_debate") as mock_lookup:
                    mock_ctx.return_value = {"test": True}
                    mock_hash.return_value = "abc"
                    mock_lookup.return_value = {
                        "bear": "bear text",
                        "bull": "bull text",
                        "adjudicator": None,
                        "model_used": "gpt-4o-mini",
                        "generated_at": datetime.now(timezone.utc).isoformat(),
                        "cache_hits": 3,
                    }
                    from fastapi.testclient import TestClient
                    from api.main import app
                    client = TestClient(app)
                    res = client.get("/api/guidance/TESTHIT/debate")
                    assert res.status_code == 200
                    body = res.json()
                    assert body["cached"] is True
                    assert body["bear"] == "bear text"

    def test_cache_miss_returns_empty(self):
        with patch("api.guidance.build_guidance_context") as mock_ctx:
            with patch("api.guidance.canonical_hash") as mock_hash:
                with patch("api.guidance.lookup_debate") as mock_lookup:
                    mock_ctx.return_value = {"test": True}
                    mock_hash.return_value = "miss"
                    mock_lookup.return_value = None
                    from fastapi.testclient import TestClient
                    from api.main import app
                    client = TestClient(app)
                    res = client.get("/api/guidance/TESTMISS/debate")
                    assert res.status_code == 200
                    body = res.json()
                    assert body["cached"] is False
                    assert body["exists"] is False


class TestPeExpansionDebateCachedEndpoint:
    def test_cache_hit_returns_cached(self):
        with patch("api.pe_expansion.build_pe_expansion_context") as mock_ctx:
            with patch("api.pe_expansion.canonical_hash") as mock_hash:
                with patch("api.pe_expansion.lookup_debate") as mock_lookup:
                    mock_ctx.return_value = {"test": True}
                    mock_hash.return_value = "abc"
                    mock_lookup.return_value = {
                        "bear": "pe bear text",
                        "bull": "pe bull text",
                        "adjudicator": None,
                        "model_used": "gpt-4o-mini",
                        "generated_at": datetime.now(timezone.utc).isoformat(),
                        "cache_hits": 5,
                    }
                    from fastapi.testclient import TestClient
                    from api.main import app
                    client = TestClient(app)
                    res = client.get("/api/pe-expansion/TESTPE/debate")
                    assert res.status_code == 200
                    body = res.json()
                    assert body["cached"] is True
                    assert body["bear"] == "pe bear text"


class TestEmailDebateSection:
    def test_guidance_email_shows_debate_when_cached(self):
        with patch("engine_core.email_service.get_latest_debate_for_symbol") as mock_debate:
            mock_debate.return_value = {
                "bear": "bear\nline2",
                "bull": "bull text",
                "model_used": "gpt",
                "cache_hits": 7,
            }
            from engine_core.email_service import build_guidance_report_email_html
            payload = {
                "symbol": "TESTEMAIL",
                "report_date": "2024-01-01",
                "verdict": "ADD ZONE",
                "achieved": [], "missed": [], "partial": [], "upcoming": [],
                "total_verified": 0,
                "integrity_signal": "",
                "accuracy": 0,
                "quarter_comparison": [],
                "integrity_timeline": [],
            }
            html = build_guidance_report_email_html(payload)
            assert "Bear Case" in html
            assert "bull text" in html
            assert "cache hits 7" in html

    def test_guidance_email_shows_placeholder_when_uncached(self):
        with patch("engine_core.email_service.get_latest_debate_for_symbol") as mock_debate:
            mock_debate.return_value = None
            from engine_core.email_service import build_guidance_report_email_html
            payload = {
                "symbol": "TESTMISS",
                "report_date": "2024-01-01",
                "verdict": "ADD ZONE",
                "achieved": [], "missed": [], "partial": [], "upcoming": [],
                "total_verified": 0,
                "integrity_signal": "",
                "accuracy": 0,
                "quarter_comparison": [],
                "integrity_timeline": [],
            }
            html = build_guidance_report_email_html(payload)
            assert "Open in the MRI app" in html
            assert "Bear Case" not in html

    def test_pe_expansion_email_shows_debate_when_cached(self):
        with patch("api.pe_expansion.get_latest_debate_for_symbol") as mock_debate:
            mock_debate.return_value = {
                "bear": "pe bear",
                "bull": "pe bull",
                "model_used": "gpt",
                "cache_hits": 2,
            }
            from api.pe_expansion import render_pe_expansion_email
            report = {
                "header": {
                    "symbol": "TESTPE", "company_name": "Test Co", "sector": "IT",
                    "pe_score": 10.0, "rank": 1, "total": 100, "bucket": "A",
                    "generated_at_iso": "2024-01-01T00:00:00Z", "generated_at_ist": "",
                },
                "coverage": {"n_promises_total": 0, "n_quote_verified": 0, "n_transcripts": 0, "n_quarter_span": 0},
                "category_breakdown": [], "top_drivers": [],
                "primary_detail": [], "secondary_detail": None,
                "totals": {"promises": 0, "verified": 0, "transcript_quarters": 0},
                "bottom_line": None, "credibility": None,
            }
            html = render_pe_expansion_email(report)
            assert "pe bear" in html
            assert "pe bull" in html


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
