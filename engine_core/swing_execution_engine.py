"""
Momentum Swing Trading Execution Engine (STEE)
Implements rule-based breakout entry and hybrid exit management.
"""
import logging
import os
import sys
from datetime import date, timedelta
import pandas as pd
import numpy as np
from psycopg2.extras import execute_batch

# Add parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engine_core.db import get_connection

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("stee")

# CONFIG
RISK_PER_TRADE_PCT = 0.01  # 1% risk
MIN_ADTV = 100_000_000     # ₹10 Cr
MAX_GAP_UP_PCT = 4.0       # 4% max gap on breakout
MAX_ATR_MULT = 2.0         # 2.0x ATR max candle range

def get_latest_regime(cur):
    cur.execute("SELECT classification, ema_200 FROM market_regime ORDER BY date DESC LIMIT 1")
    row = cur.fetchone()
    return row if row else {"classification": "NEUTRAL", "ema_200": 0}

def get_qualified_watchlist(cur):
    """
    Get stocks passing:
    EMA 50 > EMA 200
    EMA 200 Slope > 0 (Implicit in MRI condition_ema_200_slope)
    RS (90d) > 0
    Close within 15% of 6M high
    """
    cur.execute("""
        SELECT ss.symbol, ss.total_score, ss.date,
               dp.close, dp.high, dp.low, dp.open, dp.volume,
               dp.ema_10, dp.ema_50, dp.ema_200, dp.high_10d, dp.low_5d, dp.atr_14, dp.avg_volume_20d,
               dp.rolling_high_6m
        FROM stock_scores ss
        JOIN daily_prices dp ON dp.symbol = ss.symbol AND dp.date = ss.date
        WHERE ss.date = (SELECT MAX(date) FROM stock_scores)
          AND ss.condition_ema_50_200 = TRUE
          AND ss.condition_ema_200_slope = TRUE
          AND ss.condition_rs = TRUE
          AND dp.close >= dp.rolling_high_6m * 0.85
          AND dp.avg_volume_20d * dp.close >= %s
    """, (MIN_ADTV,))
    return cur.fetchall()

def log_audit_event(cur, event_type, severity, message, metadata=None):
    """Log an audit event to the system_audit_logs table."""
    try:
        import json
        cur.execute("""
            INSERT INTO system_audit_logs (event_type, severity, message, metadata)
            VALUES (%s, %s, %s, %s)
        """, (event_type, severity, message, json.dumps(metadata or {})))
    except Exception as e:
        logger.error(f"Failed to log audit event: {e}")

def process_entries(cur, regime_row, watchlist, clients):
    regime = regime_row["classification"]
    if regime == "BEARISH":
        logger.info("Regime is BEARISH. Skipping all new entries.")
        return

    # Position size modifier for SIDEWAYS regime
    size_modifier = 0.5 if regime == "SIDEWAYS" else 1.0
    
    for stock in watchlist:
        sym = stock["symbol"]
        close = float(stock["close"])
        high = float(stock["high"])
        low = float(stock["low"])
        open_p = float(stock["open"])
        high_10d = float(stock["high_10d"] or 0)
        atr = float(stock["atr_14"] or 0)
        avg_vol = float(stock["avg_volume_20d"] or 1)
        vol = float(stock["volume"] or 0)
        
        # 1. Breakout Trigger: Close > Highest High (last 10 days)
        if close <= high_10d:
            continue
            
        # 2. Volume Trigger: Volume > 1.5x 20-day Avg
        if vol < 1.5 * avg_vol:
            continue
            
        # 3. Candle Strength: Close near Day High (Top 30% of range)
        candle_range = high - low
        if candle_range > 0:
            relative_close = (close - low) / candle_range
            if relative_close < 0.7:
                continue
        else:
            continue

        # 4. No-Trade Filters
        # Gap-up > 4%
        cur.execute("SELECT close FROM daily_prices WHERE symbol = %s AND date < %s ORDER BY date DESC LIMIT 1", (sym, stock["date"]))
        prev_close_row = cur.fetchone()
        if prev_close_row:
            prev_close = float(prev_close_row["close"])
            gap = (open_p - prev_close) / prev_close * 100
            if gap > MAX_GAP_UP_PCT:
                logger.info(f"  Skipping {sym}: Gap up {gap:.1f}% > {MAX_GAP_UP_PCT}%")
                continue
        
        # Overextended: Candle range > 2x ATR
        if atr > 0 and candle_range > MAX_ATR_MULT * atr:
            logger.info(f"  Skipping {sym}: Overextended candle ({candle_range:.2f} > {MAX_ATR_MULT} * ATR)")
            continue

        # 5. Generate Signal for each client
        # Stop Loss = Lowest Low of last 5 candles (low_5d)
        stop_loss = float(stock["low_5d"] or low)
        
        # Ensure SL is valid (below entry)
        if stop_loss >= close:
            log_audit_event(cur, 'SIGNAL_REJECTED', 'WARNING', 
                           f"Stop Loss ({stop_loss:.2f}) >= Entry ({close:.2f}) for {sym}. Data anomaly?",
                           {'symbol': sym, 'close': close, 'stop_loss': stop_loss})
            stop_loss = close * 0.95 # Fallback to 5% SL
            
        risk_per_share = close - stop_loss
        target_2r = close + (2 * risk_per_share)

        for client in clients:
            client_id = client["id"]
            capital = float(client["initial_capital"] or 100000)
            
            # Risk amount = 1% of capital * size_modifier
            risk_amount = capital * RISK_PER_TRADE_PCT * size_modifier
            quantity = int(risk_amount / risk_per_share) if risk_per_share > 0 else 0
            
            if quantity <= 0:
                continue

            # Check if already in trade
            cur.execute("SELECT id FROM swing_trades WHERE client_id = %s AND symbol = %s AND status != 'CLOSED'", (client_id, sym))
            if cur.fetchone():
                continue

            # COMPLIANCE AUDIT: Double check regime and risk before execution
            if regime == "BEARISH":
                log_audit_event(cur, 'COMPLIANCE_VIOLATION', 'CRITICAL', 
                               f"Attempted to entry {sym} in BEARISH regime for client {client_id}",
                               {'symbol': sym, 'client_id': client_id})
                continue
            
            if risk_amount > (capital * 0.015): # 1.5% hard limit audit
                 log_audit_event(cur, 'RISK_VIOLATION', 'CRITICAL', 
                               f"Risk amount {risk_amount:.2f} exceeds 1.5% limit for client {client_id}",
                               {'symbol': sym, 'risk': risk_amount, 'capital': capital})
                 continue

            # Record Trade Entry
            cur.execute("""
                INSERT INTO swing_trades (client_id, symbol, entry_date, entry_price, stop_loss, take_profit_2r, quantity, risk_amount, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'OPEN')
            """, (client_id, sym, stock["date"], close, stop_loss, target_2r, quantity, risk_amount))
            
            logger.info(f"🚀 BUY SIGNAL: {sym} for Client {str(client_id)[:8]} (Qty: {quantity}, SL: {stop_loss:.2f}, 2R: {target_2r:.2f})")
            log_audit_event(cur, 'TRADE_ENTRY', 'INFO', f"STEE Entry for {sym}", {'client_id': client_id, 'qty': quantity})

def process_exits(cur, latest_prices):
    """
    Handle exits for open trades:
    1. Hard Stop: Close < Stop Loss
    2. Partial Profit: 50% exit at 2R
    3. Trailing Stop: Close < EMA 10
    """
    cur.execute("SELECT * FROM swing_trades WHERE status IN ('OPEN', 'PARTIAL_EXIT')")
    open_trades = cur.fetchall()
    
    for trade in open_trades:
        sym = trade["symbol"]
        if sym not in latest_prices:
            continue
            
        curr_price = float(latest_prices[sym]["close"])
        curr_ema10 = float(latest_prices[sym]["ema_10"] or curr_price)
        curr_date = latest_prices[sym]["date"]
        
        # 1. Hard Stop Loss
        if curr_price <= float(trade["stop_loss"]):
            cur.execute("""
                UPDATE swing_trades 
                SET status = 'CLOSED', exit_date = %s, exit_price = %s, exit_reason = 'STOP_LOSS'
                WHERE id = %s
            """, (curr_date, curr_price, trade["id"]))
            logger.info(f"🛑 STOP LOSS: {sym} closed at {curr_price:.2f}")
            log_audit_event(cur, 'TRADE_EXIT', 'INFO', f"Stop Loss hit for {sym}", {'id': trade['id'], 'price': curr_price})
            continue

        # 2. Partial Profit (at 2R)
        if trade["status"] == 'OPEN' and curr_price >= float(trade["take_profit_2r"]):
            cur.execute("""
                UPDATE swing_trades 
                SET status = 'PARTIAL_EXIT', quantity = quantity / 2
                WHERE id = %s
            """, (trade["id"],))
            logger.info(f"💰 PARTIAL PROFIT: {sym} 50% sold at {curr_price:.2f}")
            log_audit_event(cur, 'TRADE_EXIT', 'INFO', f"Partial exit (2R) for {sym}", {'id': trade['id'], 'price': curr_price})
            continue

        # 3. Trailing Stop (EMA 10)
        if curr_price < curr_ema10:
            cur.execute("""
                UPDATE swing_trades 
                SET status = 'CLOSED', exit_date = %s, exit_price = %s, exit_reason = 'TRAILING_STOP_EMA10'
                WHERE id = %s
            """, (curr_date, curr_price, trade["id"]))
            logger.info(f"📉 TRAILING EXIT: {sym} closed at {curr_price:.2f} (Below EMA-10)")
            log_audit_event(cur, 'TRADE_EXIT', 'INFO', f"Trailing exit for {sym}", {'id': trade['id'], 'price': curr_price})

def run_stee():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # 1. Get Environment
            regime_row = get_latest_regime(cur)
            logger.info(f"Market Regime: {regime_row['classification']}")
            log_audit_event(cur, 'PIPELINE_START', 'INFO', f"STEE Execution Started. Regime: {regime_row['classification']}")
            
            cur.execute("SELECT id, initial_capital FROM clients WHERE is_active = TRUE")
            clients = cur.fetchall()
            
            # 2. Get Data
            watchlist = get_qualified_watchlist(cur)
            logger.info(f"Qualified Watchlist: {len(watchlist)} stocks")
            
            # Latest prices for all symbols (for exits)
            cur.execute("""
                SELECT symbol, close, ema_10, date FROM daily_prices 
                WHERE date = (SELECT MAX(date) FROM daily_prices)
            """)
            prices = {r["symbol"]: r for r in cur.fetchall()}
            
            # 3. Execute Logic
            process_exits(cur, prices)
            process_entries(cur, regime_row, watchlist, clients)
            
            conn.commit()
            logger.info("STEE Run Complete.")
            log_audit_event(cur, 'PIPELINE_END', 'INFO', "STEE Execution Completed Successfully.")
    except Exception as e:
        conn.rollback()
        logger.exception("STEE crashed")
        # Try to log crash to audit
        try:
            with conn.cursor() as cur:
                log_audit_event(cur, 'SYSTEM_CRASH', 'CRITICAL', f"STEE Engine Crashed: {str(e)}")
                conn.commit()
        except: pass
    finally:
        conn.close()

if __name__ == "__main__":
    run_stee()
