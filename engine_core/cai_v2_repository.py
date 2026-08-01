import psycopg2.extras
import json
from typing import List, Optional
from datetime import date
from engine_core.db import get_connection
from engine_core.cai_v2_models import (
    DecisionEvaluation, Threshold, StateTransition, DecisionLedgerEntry
)
import uuid

class CaiV2Repository:
    def __init__(self):
        pass

    def save_decision_snapshot(self, eval_data: DecisionEvaluation, conn=None):
        owns_conn = False
        if conn is None:
            conn = get_connection()
            owns_conn = True

        snapshot_id = str(uuid.uuid4())
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO cai_v2_decision_snapshots (
                        id, position_id, symbol, decision_state, decision_confidence,
                        decision_stability, decision_expiry, rule_satisfaction_score,
                        why, why_not_add, triggered_rules, rule_categories,
                        portfolio_context, engine_version, rule_set_version, schema_version
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    """,
                    (
                        snapshot_id, eval_data.position_id, eval_data.symbol, eval_data.decision_state.value,
                        eval_data.decision_confidence, eval_data.decision_stability, eval_data.decision_expiry,
                        eval_data.rule_satisfaction_score, eval_data.why, eval_data.why_not_add,
                        json.dumps(eval_data.triggered_rules),
                        json.dumps([c.value for c in eval_data.rule_categories]),
                        json.dumps(eval_data.portfolio_context), eval_data.engine_version,
                        eval_data.rule_set_version, eval_data.schema_version
                    )
                )
            if owns_conn:
                conn.commit()
        finally:
            if owns_conn and not conn.closed:
                conn.close()
        return snapshot_id

    def save_thresholds(self, position_id: str, thresholds: List[Threshold], conn=None):
        owns_conn = False
        if conn is None:
            conn = get_connection()
            owns_conn = True

        try:
            with conn.cursor() as cur:
                for t in thresholds:
                    cur.execute(
                        """
                        INSERT INTO cai_v2_threshold_definitions (
                            id, position_id, threshold_type, value, confidence, reason,
                            triggered_rules, valid_from, valid_until
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            str(uuid.uuid4()), position_id, t.threshold_type.value, t.value,
                            t.confidence, t.reason, json.dumps(t.triggered_rules),
                            t.valid_from, t.valid_until
                        )
                    )
            if owns_conn:
                conn.commit()
        finally:
            if owns_conn and not conn.closed:
                conn.close()

    def save_state_transition(self, position_id: str, symbol: str, transition: StateTransition, conn=None):
        owns_conn = False
        if conn is None:
            conn = get_connection()
            owns_conn = True

        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO cai_v2_state_transitions (
                        id, position_id, symbol, from_state, to_state, transition_date, reasoning_snapshot
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        str(uuid.uuid4()), position_id, symbol,
                        transition.from_state.value if transition.from_state else None,
                        transition.to_state.value, transition.timestamp,
                        json.dumps(transition.reasoning_snapshot)
                    )
                )
            if owns_conn:
                conn.commit()
        finally:
            if owns_conn and not conn.closed:
                conn.close()

    def save_decision_ledger_entry(self, entry: DecisionLedgerEntry, conn=None):
        owns_conn = False
        if conn is None:
            conn = get_connection()
            owns_conn = True

        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO cai_v2_decision_ledger (
                        id, position_id, symbol, from_state, to_state, reasoning_snapshot,
                        confidence, stability, rule_satisfaction_score, expiry,
                        triggered_rules, threshold_references
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        str(uuid.uuid4()), entry.position_id, entry.symbol,
                        entry.from_state.value if entry.from_state else None,
                        entry.to_state.value, json.dumps(entry.reasoning_snapshot),
                        entry.confidence, entry.stability, entry.rule_satisfaction_score,
                        entry.expiry, json.dumps(entry.triggered_rules),
                        json.dumps(entry.threshold_references)
                    )
                )
            if owns_conn:
                conn.commit()
        finally:
            if owns_conn and not conn.closed:
                conn.close()

    def try_acquire_notification_lock(self, symbol: str, to_state: str, event_date: date, conn=None) -> bool:
        """
        Idempotency guard for notifications. Returns True if the lock was acquired, False if it already exists.
        """
        owns_conn = False
        if conn is None:
            conn = get_connection()
            owns_conn = True

        idempotency_key = f"{symbol}_{to_state}_{event_date.isoformat()}"
        try:
            with conn.cursor() as cur:
                try:
                    cur.execute(
                        """
                        INSERT INTO cai_v2_notification_locks (idempotency_key, symbol, to_state, event_date)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (idempotency_key, symbol, to_state, event_date)
                    )
                    if owns_conn:
                        conn.commit()
                    return True
                except psycopg2.IntegrityError:
                    if owns_conn:
                        conn.rollback()
                    return False
        finally:
            if owns_conn and not conn.closed:
                conn.close()
