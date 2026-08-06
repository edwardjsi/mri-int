import sys
import os
import time
import pandas as pd
import numpy as np
import logging

# Ensure root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engine_core.db import get_connection

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

ALGORITHM_VERSION = "DL-2.0"

def load_positions(conn):
    """Fetch all active CAI positions."""
    logger.info("Loading active CAI positions...")
    with conn.cursor() as cur:
        cur.execute("SELECT id, symbol FROM cai_position WHERE status = 'ACTIVE'")
        rows = cur.fetchall()
        positions = [{"id": r[0], "symbol": r[1]} for r in rows]
    return positions

def load_mri_inputs(conn, symbol: str):
    """
    Fetch the latest required MRI technical data for a symbol.
    Uses daily_prices to derive weekly values (Friday close).
    """
    # Fetch the last 300 daily rows to compute weekly EMAs and swing lows
    query = """
        SELECT date, open, close, high, low, volume
        FROM daily_prices
        WHERE symbol = %s
        ORDER BY date DESC
        LIMIT 300
    """
    df = pd.read_sql_query(query, conn, params=(symbol,))
    if df.empty:
        return None
    
    # Sort chronological
    df = df.sort_values('date').reset_index(drop=True)
    df['date'] = pd.to_datetime(df['date'])
    
    # Resample to weekly (Friday close)
    df_weekly = df.set_index('date').resample('W-FRI').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna().reset_index()
    
    if df_weekly.empty:
        return None
        
    # Calculate Weekly EMAs
    df_weekly['ema_20_w'] = df_weekly['close'].ewm(span=20, adjust=False).mean()
    df_weekly['ema_50_w'] = df_weekly['close'].ewm(span=50, adjust=False).mean()
    
    # Proxy for Swing Low: lowest low of the last 4 weeks (Primary)
    df_weekly['swing_low'] = df_weekly['low'].rolling(window=4, min_periods=1).min()
    
    # Calculate 14-week ATR
    df_weekly['tr'] = np.maximum(df_weekly['high'] - df_weekly['low'], 
                                 np.maximum(abs(df_weekly['high'] - df_weekly['close'].shift()), 
                                            abs(df_weekly['low'] - df_weekly['close'].shift())))
    df_weekly['atr_14'] = df_weekly['tr'].rolling(window=14, min_periods=1).mean()
    
    # Proxy for Breakout Level (Add Level): highest high of the last 10 weeks
    df_weekly['breakout_level'] = df_weekly['high'].rolling(window=10, min_periods=1).max()
    
    # Get the latest Friday close row
    latest = df_weekly.iloc[-1]
    
    return {
        "current_price": float(latest['close']),
        "ema_20_w": float(latest['ema_20_w']) if pd.notnull(latest['ema_20_w']) and len(df_weekly) >= 20 else None,
        "ema_50_w": float(latest['ema_50_w']) if pd.notnull(latest['ema_50_w']) and len(df_weekly) >= 50 else None,
        "swing_low": float(latest['swing_low']) if pd.notnull(latest['swing_low']) else None,
        "breakout_level": float(latest['breakout_level']) if pd.notnull(latest['breakout_level']) else None,
        "atr": float(latest['atr_14']) if pd.notnull(latest['atr_14']) else 0.0,
    }

def compute_thresholds(inputs: dict):
    """
    Compute ADD, ALERT, STRUCTURE, QUIT levels deterministically.
    Implements edge case logic for missing data.
    """
    cp = inputs["current_price"]
    ema_20 = inputs["ema_20_w"]
    ema_50 = inputs["ema_50_w"]
    sl = inputs["swing_low"]
    bo = inputs["breakout_level"]
    atr = inputs["atr"]
    
    # 1. Anchor: Structure Level
    if sl is not None:
        structure_level = sl
    elif ema_50 is not None:
        structure_level = ema_50
    elif ema_20 is not None:
        structure_level = ema_20
    else:
        structure_level = None
        
    # 2. Derived: Alert and Quit
    if structure_level is not None:
        alert_level = structure_level + atr
        quit_level = structure_level - (0.5 * atr)
    else:
        alert_level = None
        quit_level = None
        
    # 3. Add Level
    if bo is not None:
        add_level = bo
    else:
        add_level = cp * 1.05
        
    # Rounding to 2 decimals
    def r(val):
        return round(val, 2) if val is not None else None
        
    return {
        "quit_level": r(quit_level),
        "structure_level": r(structure_level),
        "alert_level": r(alert_level),
        "add_level": r(add_level)
    }

def evaluate_position_health(current_price: float, thresholds: dict) -> dict:
    """
    Position Evaluation Layer: Diagnoses the health and structural state
    of the position without making execution choices.
    """
    ql = thresholds["quit_level"]
    sl = thresholds["structure_level"]
    al = thresholds["alert_level"]
    add = thresholds["add_level"]
    
    if ql is None and sl is None:
        return {
            "trend": "Unknown",
            "is_broken": False,
            "is_structurally_weak": False,
            "is_alert": False,
            "eligible_for_add": False,
            "missing_data": True
        }
        
    evaluation = {
        "trend": "Healthy",
        "is_broken": False,
        "is_structurally_weak": False,
        "is_alert": False,
        "eligible_for_add": False,
        "missing_data": False
    }
    
    if ql is not None and current_price < ql:
        evaluation["trend"] = "Broken"
        evaluation["is_broken"] = True
    elif ql is not None and sl is not None and ql <= current_price < sl:
        evaluation["trend"] = "Weak"
        evaluation["is_structurally_weak"] = True
    elif sl is not None and al is not None and sl <= current_price < al:
        evaluation["trend"] = "Alert"
        evaluation["is_alert"] = True
    elif add is not None and current_price >= add:
        evaluation["eligible_for_add"] = True
        
    return evaluation

def resolve_state(evaluation: dict) -> str:
    """
    Decision Engine: Resolves the deterministic state hierarchy based purely
    on the Position Evaluation result.
    """
    if evaluation.get("missing_data"):
        return 'NOT_COMPUTED'
        
    # Priority 1: QUIT
    if evaluation.get("is_broken"):
        return 'QUIT'
        
    # Priority 2: STRUCTURE
    if evaluation.get("is_structurally_weak"):
        return 'STRUCTURE'
        
    # Priority 3: ALERT
    if evaluation.get("is_alert"):
        return 'ALERT'
        
    # Priority 4: ADD
    if evaluation.get("eligible_for_add"):
        return 'ADD'
        
    # Priority 5: HOLD
    return 'HOLD'

def validate(state: str, thresholds: dict):
    """
    Validate outputs before persistence.
    """
    valid_states = ['ADD', 'HOLD', 'ALERT', 'STRUCTURE', 'QUIT', 'NOT_COMPUTED']
    if state not in valid_states:
        raise ValueError(f"Invalid state computed: {state}")
    
    if state == 'NOT_COMPUTED':
        return # Skip further checks if missing data
        
    # Could add checks like quit <= structure <= alert if enforcing rigid geometry, 
    # but the priority ladder naturally handles crossover edge cases.

def persist(conn, holding_id: str, state: str, thresholds: dict, quality: str):
    """
    UPSERT the calculated thresholds and state into cai_position.
    """
    with conn.cursor() as cur:
        query = """
            UPDATE cai_position
            SET add_level = %s,
                alert_level = %s,
                structure_level = %s,
                quit_level = %s,
                decision_state = %s,
                threshold_quality = %s,
                decision_calculated_at = NOW(),
                decision_algorithm_version = %s
            WHERE id = %s
        """
        cur.execute(query, (
            thresholds["add_level"],
            thresholds["alert_level"],
            thresholds["structure_level"],
            thresholds["quit_level"],
            state,
            quality,
            ALGORITHM_VERSION,
            holding_id
        ))

def log_summary(metrics: dict):
    """
    Log the operational batch summary.
    """
    print("\nDecision Ladder Batch Summary")
    print("=============================")
    print(f"Algorithm: {metrics['algorithm']}")
    print(f"Processed: {metrics['processed']} positions\n")
    for state, count in metrics['states'].items():
        print(f"{state}: {count}")
    print(f"\nExecution Time: {metrics['duration']:.2f} seconds")
    print("Completed Successfully\n")

def run_decision_engine():
    start_time = time.time()
    conn = get_connection()
    
    metrics = {
        'algorithm': ALGORITHM_VERSION,
        'processed': 0,
        'states': {'ADD': 0, 'HOLD': 0, 'ALERT': 0, 'STRUCTURE': 0, 'QUIT': 0, 'NOT_COMPUTED': 0},
        'duration': 0.0
    }
    
    try:
        positions = load_positions(conn)
        
        for pos in positions:
            symbol = pos["symbol"]
            holding_id = pos["id"]
            
            # Load
            inputs = load_mri_inputs(conn, symbol)
            if not inputs or inputs["current_price"] is None:
                state = 'NOT_COMPUTED'
                thresholds = {"add_level": None, "alert_level": None, "structure_level": None, "quit_level": None}
                quality = 'LOW'
            else:
                # Compute
                thresholds = compute_thresholds(inputs)
                
                # Evaluate
                evaluation = evaluate_position_health(inputs["current_price"], thresholds)
                
                # Resolve Decision
                state = resolve_state(evaluation)
                
                # Quality flag (Stage 1 checking / basic implementation)
                quality = 'NORMAL' if state != 'NOT_COMPUTED' else 'LOW'
            
            # Validate
            validate(state, thresholds)
            
            # Persist
            persist(conn, holding_id, state, thresholds, quality)
            
            # Track metrics
            metrics['processed'] += 1
            metrics['states'][state] += 1
            
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Batch failed: {str(e)}")
        raise
    finally:
        conn.close()
        
    metrics['duration'] = time.time() - start_time
    log_summary(metrics)

if __name__ == "__main__":
    run_decision_engine()
