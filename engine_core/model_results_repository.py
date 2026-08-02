import json
import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from decimal import Decimal

from engine_core.db import get_connection

@dataclass(frozen=True)
class ModelResult:
    """Standardized envelope for any investment model result."""
    symbol: str
    model_id: str
    model_version: str
    evaluation_date: datetime.date
    status: Optional[str] = None
    score: Optional[Decimal] = None
    payload: Optional[Dict[str, Any]] = None
    explain_node_id: Optional[str] = None
    execution_ms: Optional[int] = None
    error_message: Optional[str] = None
    
    @classmethod
    def from_row(cls, row: dict) -> 'ModelResult':
        """Construct from a Psycopg2 DictRow."""
        return cls(
            symbol=row['symbol'],
            model_id=row['model_id'],
            model_version=row['model_version'],
            evaluation_date=row['evaluation_date'],
            status=row['status'],
            score=row['score'],
            payload=row['payload'],
            explain_node_id=str(row['explain_node_id']) if row.get('explain_node_id') else None,
            execution_ms=row.get('execution_ms'),
            error_message=row.get('error_message'),
        )


class ModelResultRepository:
    """
    Append-only event store for investment model outputs.
    This repository is strictly generic and knows nothing about CANSLIM, RRG, etc.
    """
    def __init__(self, conn: Any = None):
        self._provided_conn = conn

    def _get_conn(self):
        return self._provided_conn if self._provided_conn else get_connection()

    def _close_if_needed(self, conn: Any):
        if not self._provided_conn:
            conn.close()

    def save(self, result: ModelResult) -> None:
        """Upsert the model result based on the daily evaluation unique constraint."""
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO model_results (
                        symbol, model_id, model_version, evaluation_date, 
                        status, score, payload, explain_node_id, execution_ms, error_message
                    ) VALUES (
                        %(symbol)s, %(model_id)s, %(model_version)s, %(evaluation_date)s,
                        %(status)s, %(score)s, %(payload)s, %(explain_node_id)s, %(execution_ms)s, %(error_message)s
                    )
                    ON CONFLICT (symbol, model_id, model_version, evaluation_date) 
                    DO UPDATE SET
                        status = EXCLUDED.status,
                        score = EXCLUDED.score,
                        payload = EXCLUDED.payload,
                        explain_node_id = EXCLUDED.explain_node_id,
                        execution_ms = EXCLUDED.execution_ms,
                        error_message = EXCLUDED.error_message
                    """,
                    {
                        "symbol": result.symbol,
                        "model_id": result.model_id,
                        "model_version": result.model_version,
                        "evaluation_date": result.evaluation_date,
                        "status": result.status,
                        "score": result.score,
                        "payload": json.dumps(result.payload) if result.payload is not None else None,
                        "explain_node_id": result.explain_node_id,
                        "execution_ms": result.execution_ms,
                        "error_message": result.error_message
                    }
                )
            conn.commit()
        finally:
            self._close_if_needed(conn)

    def latest(self, symbol: str) -> List[ModelResult]:
        """Fetch the latest evaluation for ALL models for a given symbol."""
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                # Use DISTINCT ON to get the latest evaluation_date per model_id
                cur.execute(
                    """
                    SELECT DISTINCT ON (model_id)
                        symbol, model_id, model_version, evaluation_date, 
                        status, score, payload, explain_node_id, execution_ms, error_message
                    FROM model_results
                    WHERE symbol = %s
                    ORDER BY model_id, evaluation_date DESC, model_version DESC
                    """,
                    (symbol,)
                )
                rows = cur.fetchall()
                return [ModelResult.from_row(dict(r)) for r in rows]
        finally:
            self._close_if_needed(conn)

    def latest_for_model(self, symbol: str, model_id: str) -> Optional[ModelResult]:
        """Fetch the latest evaluation of a SPECIFIC model for a given symbol."""
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT 
                        symbol, model_id, model_version, evaluation_date, 
                        status, score, payload, explain_node_id, execution_ms, error_message
                    FROM model_results
                    WHERE symbol = %s AND model_id = %s
                    ORDER BY evaluation_date DESC, model_version DESC
                    LIMIT 1
                    """,
                    (symbol, model_id)
                )
                row = cur.fetchone()
                return ModelResult.from_row(dict(row)) if row else None
        finally:
            self._close_if_needed(conn)

    def history(self, symbol: str, days: int = 30) -> List[ModelResult]:
        """Fetch historical evaluations across all models for a given symbol."""
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT 
                        symbol, model_id, model_version, evaluation_date, 
                        status, score, payload, explain_node_id, execution_ms, error_message
                    FROM model_results
                    WHERE symbol = %s 
                      AND evaluation_date >= CURRENT_DATE - INTERVAL '%s days'
                    ORDER BY evaluation_date DESC, model_id
                    """,
                    (symbol, days)
                )
                rows = cur.fetchall()
                return [ModelResult.from_row(dict(r)) for r in rows]
        finally:
            self._close_if_needed(conn)

    def history_for_model(self, symbol: str, model_id: str, days: int = 30) -> List[ModelResult]:
        """Fetch historical evaluations of a specific model for a given symbol."""
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT 
                        symbol, model_id, model_version, evaluation_date, 
                        status, score, payload, explain_node_id, execution_ms, error_message
                    FROM model_results
                    WHERE symbol = %s 
                      AND model_id = %s
                      AND evaluation_date >= CURRENT_DATE - INTERVAL '%s days'
                    ORDER BY evaluation_date DESC
                    """,
                    (symbol, model_id, days)
                )
                rows = cur.fetchall()
                return [ModelResult.from_row(dict(r)) for r in rows]
        finally:
            self._close_if_needed(conn)

    def latest_for_symbols(self, symbols: List[str]) -> List[ModelResult]:
        """Fetch the latest evaluation of ALL models for a LIST of symbols (e.g. for Watchlist rendering)."""
        if not symbols:
            return []
            
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT DISTINCT ON (symbol, model_id)
                        symbol, model_id, model_version, evaluation_date, 
                        status, score, payload, explain_node_id, execution_ms, error_message
                    FROM model_results
                    WHERE symbol = ANY(%s)
                    ORDER BY symbol, model_id, evaluation_date DESC, model_version DESC
                    """,
                    (symbols,)
                )
                rows = cur.fetchall()
                return [ModelResult.from_row(dict(r)) for r in rows]
        finally:
            self._close_if_needed(conn)
