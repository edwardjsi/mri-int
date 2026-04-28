import logging
import json
from datetime import datetime
from engine_core.db import get_connection
from engine_fundamental.agents import (
    revenue_quality_agent, margin_quality_agent, operating_leverage_agent,
    working_capital_agent, capital_efficiency_agent, business_evolution_agent,
    financial_translation_agent
)
from engine_qualitative.collector import build_qil_input
from engine_qualitative.extractor import extract_signals
from engine_qualitative.scorer import score_signals
from engine_qualitative.cross_check import cross_check
from engine_fundamental.trajectory import compute_score_velocity, detect_score_trend

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_financial_history(symbol):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT year, revenue, ebitda, net_profit, total_assets, 
               capital_employed, receivables, inventory, debt, equity
        FROM fundamental_financials
        WHERE symbol = %s
        ORDER BY year ASC
    """, (symbol,))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_qil_sources_for_ticker(symbol):
    from engine_core.db import get_connection
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT concall_url, annual_report_url FROM qil_sources WHERE symbol = %s", (symbol,))
    row = cur.fetchone()
    conn.close()
    if not row: return []
    
    sources = []
    if row['concall_url']:
        sources.append({"url": row['concall_url'], "type": "concall", "date": datetime.now().strftime("%Y-%m")})
    if row['annual_report_url']:
        sources.append({"url": row['annual_report_url'], "type": "annual_report", "date": datetime.now().strftime("%Y-%m")})
    return sources

def run_quality_pipeline(symbol):
    history = get_financial_history(symbol)
    if not history:
        logger.error(f"No financial history for {symbol}. Run collector first.")
        return None

    # Execute all agents
    results = {
        "revenue_growth": revenue_quality_agent(history),
        "margin_quality": margin_quality_agent(history),
        "operating_leverage": operating_leverage_agent(history),
        "working_capital": working_capital_agent(history),
        "capital_efficiency": capital_efficiency_agent(history),
        "business_evolution": business_evolution_agent(history),
        "financial_translation": financial_translation_agent(history)
    }

    # Weights and scoring
    weights = {
        "capital_efficiency": 0.25,
        "revenue_growth": 0.20,
        "margin_quality": 0.15,
        "operating_leverage": 0.10,
        "working_capital": 0.15,
        "financial_translation": 0.10,
        "business_evolution": 0.05
    }
    
    base_score = sum(results[k]["score"] * weights[k] for k in weights) * 10
    
    flags = []
    penalty = 0
    reject = False
    
    # Critical rejection rule: ROCE < WACC
    if results['capital_efficiency']['score'] < 3:
        penalty += 20
        reject = True
        flags.append("🚨 VALUE DESTRUCTION: ROCE < WACC")

    # QIL ADJUSTMENT
    qil_score = 0
    qil_flags = []
    qil_adjustment = 0
    
    if not reject:
        try:
            sources = get_qil_sources_for_ticker(symbol)
            if sources:
                docs = build_qil_input(symbol, sources)
                signals = extract_signals(docs)
                qil_score, s_flags = score_signals(signals)
                
                # scale Q-score (0–10) → (-3 to +3 impact)
                qil_adjustment = (qil_score - 5) * 0.6
                
                agent_map = {
                    "margin_quality": results['margin_quality']['score'],
                    "working_capital": results['working_capital']['score']
                }
                cross_penalty, c_flags = cross_check(qil_score, agent_map)
                
                penalty += cross_penalty
                qil_flags = s_flags + c_flags
        except Exception as e:
            print(f"QIL Engine failed for {symbol}: {e}")

    final_score = max(0, min(100, base_score + qil_adjustment - penalty))
    
    # Overall categorization
    if reject:
        category = "REJECT"
    elif final_score >= 80:
        category = "HIGH_QUALITY"
    elif final_score >= 70:
        category = "EARLY_COMPOUNDER"
    elif final_score >= 60:
        category = "WATCHLIST"
    else:
        category = "REJECT"

    # Trajectory Integration
    prev_score = None
    score_change = 0
    velocity = 0
    
    conn = get_connection()
    cur = conn.cursor()
    
    # Get last known score from history
    cur.execute("SELECT score FROM quality_verdicts WHERE symbol = %s", (symbol,))
    row = cur.fetchone()
    if row:
        prev_score = float(row[0])
        score_change = final_score - prev_score
        
    # Get score history for velocity
    cur.execute("SELECT score FROM quality_verdicts_history WHERE symbol = %s ORDER BY recorded_at DESC LIMIT 5", (symbol,))
    history_rows = cur.fetchall()
    score_history = [float(r[0]) for r in reversed(history_rows)]
    score_history.append(final_score)
    
    velocity = compute_score_velocity(score_history)
    trend = detect_score_trend(score_history)
    
    # Persistence
    cur.execute("""
        INSERT INTO quality_verdicts (
            symbol, score, category, reasoning, flags,
            prev_score, score_change, velocity,
            revenue_score, margin_score, leverage_score, wc_score, roce_score, evolution_score,
            qil_score, qil_flags
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (symbol) DO UPDATE SET
            prev_score = EXCLUDED.prev_score,
            score_change = EXCLUDED.score_change,
            velocity = EXCLUDED.velocity,
            score = EXCLUDED.score,
            category = EXCLUDED.category,
            reasoning = EXCLUDED.reasoning,
            flags = EXCLUDED.flags,
            revenue_score = EXCLUDED.revenue_score,
            margin_score = EXCLUDED.margin_score,
            leverage_score = EXCLUDED.leverage_score,
            wc_score = EXCLUDED.wc_score,
            roce_score = EXCLUDED.roce_score,
            evolution_score = EXCLUDED.evolution_score,
            qil_score = EXCLUDED.qil_score,
            qil_flags = EXCLUDED.qil_flags,
            updated_at = NOW()
    """, (
        symbol, final_score, category, f"Quality Analysis for {symbol}. Fundamental strength score: {base_score:.1f}", 
        flags,
        prev_score, score_change, velocity,
        results['revenue_growth']['score'], results['margin_quality']['score'],
        results['operating_leverage']['score'], results['working_capital']['score'],
        results['capital_efficiency']['score'], results['business_evolution']['score'],
        qil_score, qil_flags
    ))
    
    # Record in history
    cur.execute("INSERT INTO quality_verdicts_history (symbol, score) VALUES (%s, %s)", (symbol, final_score))
    
    conn.commit()
    cur.close()
    conn.close()
    
    logger.info(f"Quality Verdict for {symbol}: {category} ({final_score:.1f}/100) | Change: {score_change:+.1f} | Velocity: {velocity:.1f} | Trend: {trend}")
    
    logger.info(f"Quality Verdict for {symbol}: {category} ({final_score:.1f}/100)")
    return {
        "symbol": symbol,
        "score": final_score,
        "category": category,
        "flags": flags,
        "agents": results
    }

if __name__ == "__main__":
    run_quality_pipeline("RELIANCE.NS")
