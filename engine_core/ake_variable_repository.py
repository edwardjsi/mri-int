import logging
from typing import List, Dict, Any, Optional
import uuid
import datetime

from engine_core.db import get_connection

logger = logging.getLogger(__name__)

class VariableRegistryRepository:
    def __init__(self, conn=None):
        self.conn = conn or get_connection()
    
    def close(self):
        # We don't close the shared connection unless we explicitly want to,
        # but provide the method for compatibility.
        pass

    def get_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Fetch all variables in a specific state, along with their occurrences and aliases."""
        cur = self.conn.cursor()
        try:
            cur.execute(
                """
                SELECT id, canonical_name, section, data_type, status, created_at
                FROM ake_variable
                WHERE status = %s
                ORDER BY created_at DESC
                """,
                (status,)
            )
            rows = cur.fetchall()
            
            variables = []
            for r in rows:
                var_id = r[0]
                
                # Fetch aliases
                cur.execute("SELECT alias FROM ake_variable_alias WHERE variable_id = %s", (var_id,))
                aliases = [a[0] for a in cur.fetchall()]
                
                # Fetch occurrences
                cur.execute(
                    """
                    SELECT company_id, raw_name, value, confidence, extractor_version
                    FROM ake_variable_occurrence
                    WHERE variable_id = %s
                    """,
                    (var_id,)
                )
                occ_rows = cur.fetchall()
                companies = list(set([o[0] for o in occ_rows]))
                raw_names = list(set([o[1] for o in occ_rows]))
                
                # We'll use the most frequent raw_name as the primary display name for UI
                primary_raw_name = raw_names[0] if raw_names else ""
                
                variables.append({
                    "id": str(var_id),
                    "rawName": primary_raw_name,
                    "canonicalName": r[1],
                    "section": r[2],
                    "dataType": r[3],
                    "status": r[4],
                    "confidence": occ_rows[0][3] if occ_rows else 0.0,
                    "occurrences": len(occ_rows),
                    "companies": companies,
                    "aliases": aliases
                })
            
            return variables
        finally:
            cur.close()

    def promote(self, var_id: str, user_id: str = "system", reason: str = "") -> None:
        """Promote a variable to CANONICAL."""
        cur = self.conn.cursor()
        try:
            # 1. Update status
            cur.execute(
                "UPDATE ake_variable SET status = 'CANONICAL' WHERE id = %s AND status = 'RESERVE'",
                (var_id,)
            )
            if cur.rowcount == 0:
                raise Exception(f"Variable {var_id} not found or not in RESERVE state")
            
            # 2. Record history
            cur.execute(
                """
                INSERT INTO ake_promotion_history (variable_id, action, user_id, reason)
                VALUES (%s, 'PROMOTED', %s, %s)
                """,
                (var_id, user_id, reason)
            )
            
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            raise e
        finally:
            cur.close()

    def reject(self, var_id: str, user_id: str = "system", reason: str = "") -> None:
        """Reject a variable."""
        cur = self.conn.cursor()
        try:
            # 1. Update status
            cur.execute(
                "UPDATE ake_variable SET status = 'DEPRECATED' WHERE id = %s",
                (var_id,)
            )
            if cur.rowcount == 0:
                raise Exception(f"Variable {var_id} not found")
            
            # 2. Record history
            cur.execute(
                """
                INSERT INTO ake_promotion_history (variable_id, action, user_id, reason)
                VALUES (%s, 'REJECTED', %s, %s)
                """,
                (var_id, user_id, reason)
            )
            
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            raise e
        finally:
            cur.close()

    def merge(self, source_id: str, target_canonical_name: str, user_id: str = "system", reason: str = "") -> None:
        """Merge source variable into a target canonical variable."""
        cur = self.conn.cursor()
        try:
            # 1. Find Target Variable
            cur.execute(
                "SELECT id FROM ake_variable WHERE canonical_name = %s AND status = 'CANONICAL'",
                (target_canonical_name,)
            )
            target = cur.fetchone()
            if not target:
                raise Exception(f"Target CANONICAL variable '{target_canonical_name}' not found")
            target_id = target[0]
            
            # 2. Find Source Variable to get its raw names
            cur.execute(
                "SELECT raw_name FROM ake_variable_occurrence WHERE variable_id = %s",
                (source_id,)
            )
            raw_names = list(set([r[0] for r in cur.fetchall()]))
            
            # 3. Add aliases to Target
            for raw_name in raw_names:
                cur.execute(
                    "INSERT INTO ake_variable_alias (variable_id, alias) VALUES (%s, %s)",
                    (target_id, raw_name)
                )
                
            # 4. Mark Source as MERGED
            cur.execute(
                "UPDATE ake_variable SET status = 'MERGED' WHERE id = %s",
                (source_id,)
            )
            
            # 5. Record History
            cur.execute(
                """
                INSERT INTO ake_promotion_history (variable_id, action, user_id, reason)
                VALUES (%s, 'MERGED', %s, %s)
                """,
                (source_id, user_id, reason)
            )
            
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            raise e
        finally:
            cur.close()
