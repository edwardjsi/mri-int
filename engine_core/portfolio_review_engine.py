import logging
from datetime import date
from engine_core.db import get_connection

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Risk classification thresholds (weighted misalignment %)
RISK_THRESHOLDS = {
    "LOW": 0.25,
    "MODERATE": 0.50,
    "HIGH": 0.75,
}

RISK_DESCRIPTIONS = {
    "LOW": "Portfolio well-aligned with regime",
    "MODERATE": "Some exposure to weak stocks",
    "HIGH": "Significant holdings below 200 EMA",
    "EXTREME": "Portfolio severely misaligned",
}


def classify_risk(risk_score):
    """Classify aggregate risk score into Low/Moderate/High/Extreme."""
    if risk_score < RISK_THRESHOLDS["LOW"]:
        return "LOW"
    elif risk_score < RISK_THRESHOLDS["MODERATE"]:
        return "MODERATE"
    elif risk_score < RISK_THRESHOLDS["HIGH"]:
        return "HIGH"
    else:
        return "EXTREME"


def _compute_holding_risk_factor(score, below_ema200, regime):
    """
    Compute a 0.0–1.0 risk factor for a single holding.
    Based on 0-100 MRI score.
    """
    s = score if score is not None else 50
    # Linear risk: 100 score = 0 risk, 0 score = 1.0 risk
    risk = (100 - s) / 100.0

    if below_ema200:
        risk = min(risk + 0.20, 1.0)  # Moderate penalty for being below trend

    if regime == "BEAR":
        risk = min(risk + 0.20, 1.0)  # Market penalty

    return round(max(0.0, risk), 2)


def analyze_portfolio(holdings, conn=None):
    """
    Analyze a portfolio against MRI intelligence.

    Args:
        holdings: list of dicts with keys: symbol, quantity, avg_cost
        conn: optional DB connection (will create one if not provided)

    Returns:
        dict with keys: regime, risk_level, risk_score, holdings, summary, analyzed_date
    """
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True

    try:
        return _analyze(holdings, conn)
    finally:
        if should_close:
            conn.close()


def _analyze(holdings, conn):
    """Core analysis logic."""
    from psycopg2.extras import RealDictCursor
    from decimal import Decimal
    cur = conn.cursor(cursor_factory=RealDictCursor)

    def _to_float(v, default: float = 0.0) -> float:
        if v is None:
            return default
        try:
            if isinstance(v, Decimal):
                return float(v)
            return float(v)
        except Exception:
            return default

    if not holdings:
        return {
            "regime": None,
            "risk_level": None,
            "risk_score": 0,
            "holdings": [],
            "summary": "No holdings provided.",
            "analyzed_date": str(date.today()),
        }

    # 1. Current market regime
    cur.execute("""
        SELECT date, classification, sma_200, sma_200_slope_20
        FROM market_regime ORDER BY date DESC LIMIT 1
    """)
    regime_row = cur.fetchone()
    regime = regime_row["classification"] if regime_row else "NEUTRAL"
    regime_date = str(regime_row["date"]) if regime_row else None

    # 2. Collect symbols (de-duplicated)
    symbols = list(set([h["symbol"].upper().strip() for h in holdings]))
    symbol_tuple = tuple(symbols)

    # 3. Latest stock scores for submitted symbols
    cur.execute("""
        SELECT DISTINCT ON (ss.symbol)
        ss.symbol, ss.total_score, ss.date,
        ss.condition_ema_50_200, ss.condition_ema_200_slope,
        ss.condition_6m_high, ss.condition_volume, ss.condition_rs,
        ss.condition_breakout_10d, ss.condition_price_quality
        FROM stock_scores ss
        WHERE ss.symbol IN %s
        ORDER BY ss.symbol, ss.date DESC
    """, (symbol_tuple,))
    scores_by_symbol = {r["symbol"]: r for r in cur.fetchall()}

    # 4. Latest prices + indicators
    cur.execute("""
        SELECT DISTINCT ON (dp.symbol) 
                dp.symbol, dp.close, dp.ema_50, dp.ema_200, dp.rs_90d,
                dp.avg_volume_20d, dp.date
        FROM daily_prices dp
        WHERE dp.symbol IN %s
        ORDER BY dp.symbol, dp.date DESC
    """, (symbol_tuple,))
    prices_by_symbol = {r["symbol"]: r for r in cur.fetchall()}

    cur.close()

    # 5. Per-holding analysis
    analyzed_holdings = []
    total_value = 0.0

    # First pass: compute total portfolio value
    for h in holdings:
        sym = h["symbol"].upper().strip()
        qty = _to_float(h.get("quantity", 0), 0.0)
        price_data = prices_by_symbol.get(sym)
        current_price = float(price_data["close"]) if price_data and price_data["close"] else _to_float(h.get("avg_cost", 0), 0.0)
        total_value += qty * current_price

    if total_value == 0:
        total_value = 1.0  # avoid division by zero

    # Second pass: full analysis
    weighted_risk_sum = 0.0
    unrecognized = []

    for h in holdings:
        sym = h["symbol"].upper().strip()
        qty = _to_float(h.get("quantity", 0), 0.0)
        avg_cost = _to_float(h.get("avg_cost", 0), 0.0)

        price_data = prices_by_symbol.get(sym)
        score_data = scores_by_symbol.get(sym)

        current_price = float(price_data["close"]) if price_data and price_data["close"] else None
        ema_200 = float(price_data["ema_200"]) if price_data and price_data["ema_200"] else None
        ema_50 = float(price_data["ema_50"]) if price_data and price_data["ema_50"] else None
        rs_90d = float(price_data["rs_90d"]) if price_data and price_data["rs_90d"] else None

        score = score_data["total_score"] if score_data else None
        below_ema200 = (current_price < ema_200) if (current_price and ema_200) else None

        # Portfolio weight
        holding_value = qty * (current_price or avg_cost or 0.0)
        weight = holding_value / total_value

        # Risk factor
        if score is not None:
            risk_factor = _compute_holding_risk_factor(score, below_ema200 or False, regime)
        else:
            risk_factor = 0.75  # unknown stocks get high-ish risk
            unrecognized.append(sym)

        risk_contribution = weight * risk_factor
        weighted_risk_sum += risk_contribution

        # P&L
        pnl_pct = None
        if current_price and avg_cost and avg_cost > 0:
            pnl_pct = round(((current_price - avg_cost) / avg_cost) * 100, 2)

        # Alignment label (0-100 scale)
        if score is None:
            alignment = "UNKNOWN"
        elif score >= 75:
            alignment = "STRONG" if regime != "BEAR" else "ALIGNED"
        elif score <= 40:
            alignment = "WEAK"
        else:
            alignment = "NEUTRAL"

        holding_result = {
            "symbol": sym,
            "quantity": float(qty),
            "avg_cost": float(avg_cost),
            "current_price": float(current_price) if current_price else None,
            "pnl_pct": float(pnl_pct) if pnl_pct is not None else None,
            "weight_pct": float(round(weight * 100, 2)),
            "score": score,
            "conditions": None,
            "below_200ema": below_ema200,
            "ema_50": float(ema_50) if ema_50 else None,
            "ema_200": float(ema_200) if ema_200 else None,
            "rs_90d": float(rs_90d) if rs_90d else None,
            "alignment": alignment,
            "risk_factor": float(round(risk_factor, 2)),
            "risk_contribution_pct": float(round(risk_contribution * 100, 2)),
            "breakout_candidate": bool(score_data["condition_breakout_10d"]) if score_data and score_data.get("condition_breakout_10d") is not None and score is not None and score >= 60 else False,
        }

        # Add score condition breakdown if available
        if score_data:
            holding_result["conditions"] = {
                "ema_50_above_200": score_data["condition_ema_50_200"],
                "ema_200_slope_positive": score_data["condition_ema_200_slope"],
                "at_6m_high": score_data["condition_6m_high"],
                "volume_surge": score_data["condition_volume"],
                "relative_strength": score_data["condition_rs"],
                "breakout_10d": score_data["condition_breakout_10d"],
                "price_quality": score_data["condition_price_quality"],
            }

        analyzed_holdings.append(holding_result)

    # 6. Aggregate risk
    risk_score = round(weighted_risk_sum, 4)
    risk_level = classify_risk(risk_score)

    # 7. Summary text
    n_total = len(analyzed_holdings)
    n_weak = sum(1 for h in analyzed_holdings if h["alignment"] == "WEAK")
    n_below_ema = sum(1 for h in analyzed_holdings if h["below_200ema"] is True)

    summary_parts = [
        f"Market Regime: {regime}.",
        f"Portfolio Risk: {risk_level} ({risk_score:.0%} weighted risk).",
        f"{n_total} holdings analyzed.",
    ]
    if n_weak > 0:
        summary_parts.append(f"{n_weak} stock(s) have weak trend scores (≤40).")
    if n_below_ema > 0:
        summary_parts.append(f"{n_below_ema} stock(s) trading below their 200 EMA.")
    if unrecognized:
        summary_parts.append(f"{len(unrecognized)} symbol(s) not found in MRI universe: {', '.join(unrecognized)}.")

    return {
        "regime": regime,
        "regime_date": regime_date,
        "risk_level": risk_level,
        "risk_level_description": RISK_DESCRIPTIONS[risk_level],
        "risk_score": float(risk_score),
        "holdings": analyzed_holdings,
        "summary": " ".join(summary_parts),
        "analyzed_date": str(date.today()),
    }


def analyze_single_stock(symbol):
    """Convenience for one-off CLI check."""
    return analyze_portfolio([{"symbol": symbol, "quantity": 1, "avg_cost": 0}])


def update_all_breakout_candidates(conn=None):
    """
    EOD pipeline step: for every client holding, check if the stock is a breakout
    candidate today and update client_external_holdings.breakout_candidate.

    A breakout candidate = condition_breakout_10d = True AND total_score >= 60.
    Runs after market close so the Risk Audit page reflects today's signals.
    """
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True

    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT ON (eh.client_id, eh.symbol)
                eh.client_id, eh.symbol, eh.id,
                ss.condition_breakout_10d, ss.total_score
            FROM client_external_holdings eh
            LEFT JOIN LATERAL (
                SELECT symbol, condition_breakout_10d, total_score
                FROM stock_scores
                WHERE symbol = eh.symbol
                ORDER BY date DESC
                LIMIT 1
            ) ss ON true
            WHERE eh.symbol IS NOT NULL
        """)
        rows = cur.fetchall()
        updated = 0
        for row in rows:
            # eh_id is at index 2, breakout_10d at index 3, total_score at index 4
            eh_id = row[2]
            breakout_10d = row[3]
            total_score = row[4]
            is_candidate = (
                breakout_10d is True and
                total_score is not None and
                total_score >= 60
            )
            cur.execute("""
                UPDATE client_external_holdings
                SET breakout_candidate = %s, updated_at = NOW()
                WHERE id = %s
            """, (is_candidate, eh_id))
            updated += 1
        conn.commit()
        cur.close()
        logger.info(f"Breakout candidate update complete: {updated} holdings evaluated")
        return updated
    except Exception as e:
        logger.error(f"Breakout candidate update failed: {e}")
        conn.rollback()
        raise
    finally:
        if should_close:
            conn.close()


def print_terminal_report(result):
    """Fancy CLI output."""
    print(f"\n{'='*65}")
    print(f" MRI PORTFOLIO RISK AUDIT | {result['analyzed_date']}")
    print(f"{'='*65}")
    print(f" MARKET REGIME: {result['regime']} (as of {result['regime_date']})")
    print(f" OVERALL RISK:  {result['risk_level']} ({result['risk_score']:.0%})")
    print(f"{'='*65}")
    print(f" {'SYMBOL':<10} | {'SCORE':<5} | {'ALIGN':<10} | {'WEIGHT':<7} | {'RISK':<7} | {'BELOW 200 EMA'}")
    print(f" {'-'*10}-+-{'-'*5}-+-{'-'*10}-+-{'-'*7}-+-{'-'*7}-+-{'-'*13}")
    
    for h in result["holdings"]:
        sym = h["symbol"]
        score = h["score"] if h["score"] is not None else "N/A"
        align = h["alignment"]
        weight = f"{h['weight_pct']}%"
        risk = f"{h['risk_factor']:.2f}"
        if h["below_200ema"] is True:
            below = "⚠️ YES"
        elif h["below_200ema"] is False:
            below = "✅ NO"
        else:
            below = "?"
        print(f" {sym:<10} | {str(score):<5} | {align:<10} | {weight:<7} | {risk:<7} | {below}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    import json
    import argparse
    import pandas as pd

    parser = argparse.ArgumentParser(description="Portfolio Review Engine — MRI Risk Analysis")
    parser.add_argument("--holdings", type=str, help='JSON array of holdings')
    parser.add_argument("--stock", type=str, help="Quick single-stock analysis (e.g. --stock RELIANCE)")
    parser.add_argument("--file", type=str, help="Path to JSON file with holdings array")
    parser.add_argument("--csv", type=str, help="Path to CSV file with holdings (must have 'symbol', 'quantity', 'avg_cost' columns)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON instead of terminal report")

    args = parser.parse_args()

    result = None

    if args.stock:
        result = analyze_single_stock(args.stock)
    elif args.holdings:
        portfolio = json.loads(args.holdings)
        result = analyze_portfolio(portfolio)
    elif args.file:
        with open(args.file) as f:
            portfolio = json.load(f)
        result = analyze_portfolio(portfolio)
    elif args.csv:
        try:
            df = pd.read_csv(args.csv)
            portfolio = []
            # Check required columns loosely
            orig_cols = list(df.columns)
            cols = [str(c).strip().lower() for c in orig_cols]
            
            sym_col = None
            qty_col = None
            cost_col = None
            
            for i, c in enumerate(cols):
                if not sym_col and c in ('symbol', 'ticker', 'instrument'):
                    sym_col = orig_cols[i]
                if not qty_col and c in ('quantity', 'shares', 'qty', 'vol', 'volume'):
                    qty_col = orig_cols[i]
                if not cost_col and ('cost' in c or 'price' in c or 'buy' in c):
                    cost_col = orig_cols[i]
            
            if not sym_col:
                print("Error: Could not find a 'symbol' column in CSV.")
                exit(1)
            
            for _, row in df.iterrows():
                sym = str(row[sym_col]).upper().strip()
                if not sym or sym == 'NAN': continue
                portfolio.append({
                    "symbol": sym,
                    "quantity": float(row[qty_col]) if qty_col and pd.notna(row[qty_col]) else 0.0,
                    "avg_cost": float(row[cost_col]) if cost_col and pd.notna(row[cost_col]) else 0.0,
                })
            result = analyze_portfolio(portfolio)
        except Exception as e:
            print(f"Error reading CSV: {e}")
            exit(1)
    else:
        logger.info("Running demo with sample portfolio...")
        sample = [
            {"symbol": "RELIANCE", "quantity": 10, "avg_cost": 2500.0},
            {"symbol": "TCS", "quantity": 5, "avg_cost": 3800.0},
            {"symbol": "INFY", "quantity": 20, "avg_cost": 1500.0},
        ]
        result = analyze_portfolio(sample)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print_terminal_report(result)
