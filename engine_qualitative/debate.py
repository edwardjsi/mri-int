import os
import json
import logging
from engine_core.db import get_connection
from engine_fundamental.agents import (
    revenue_quality_agent, margin_quality_agent, operating_leverage_agent,
    working_capital_agent, capital_efficiency_agent, business_evolution_agent,
    financial_translation_agent
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEBATE_PROMPT = """
You are a forensic equity analyst. Your job is to analyze a company that passed our 7-point quality screen and produce a critical "Debate Report."

You have access to:
1. The company's 7 fundamental agent scores (revenue, margins, leverage, working capital, ROCE, evolution, translation)
2. Its technical 7-point MRI score (EMA, slope, RS, momentum, volume, breakout, price quality)
3. Its financial history (5-10 years of revenue, profit, debt, etc.)

Your task: Write a sharp, specific analysis covering:

## 1. GUIDANCE VS REALITY
- What does management claim vs what the numbers show?
- Are revenue growth claims backed by cash flows?
- Is margin expansion real (operational) or fake (accounting)?

## 2. NUANCES
- Subtle improvements that most analysts miss
- Working capital cycles improving or deteriorating
- Hidden leverage or off-balance-sheet risks

## 3. GLARING MISTAKES
- Past guidance misses or over-promises
- Capital allocation errors (bad acquisitions, excessive debt)
- Sector peers doing better — what are they seeing that this company isn't?

## 4. VERDICT
- Final score out of 10
- Would you buy at current price? Why or why not?
- What would change your mind?

Return JSON:
{
  "guidance_vs_reality": "...",
  "nuances": ["...", "..."],
  "glaring_mistakes": ["...", "..."],
  "verdict": {
    "score": 7,
    "buy_recommendation": "BUY / HOLD / AVOID",
    "reason": "...",
    "would_change_my_mind": "..."
  }
}

Be specific. Use numbers. Be skeptical. No fluff.
"""

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

def get_quality_verdict(symbol):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM quality_verdicts WHERE symbol = %s", (symbol,))
    row = cur.fetchone()
    conn.close()
    return row

def get_mri_scores(symbol):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT total_score, date,
               condition_ema_50_200, condition_ema_200_slope,
               condition_6m_high, condition_volume, condition_rs,
               condition_breakout_10d, condition_price_quality
        FROM stock_scores
        WHERE symbol = %s
        ORDER BY date DESC LIMIT 1
    """, (symbol,))
    row = cur.fetchone()
    conn.close()
    return row

def run_debate(symbol):
    client = None
    try:
        from openai import OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return {"error": "OPENAI_API_KEY not set in environment"}
        # Create client without explicit proxies argument to avoid TypeError with newer OpenAI/Httpx versions
        client = OpenAI(api_key=api_key)
    except ImportError:
        return {"error": "OpenAI package not installed"}

    verdict = get_quality_verdict(symbol)
    mri = get_mri_scores(symbol)
    history = get_financial_history(symbol)

    if not verdict and not history:
        return {"error": f"No data found for {symbol}. Run QIF pipeline first."}

    evidence_parts = []

    if verdict:
        verdict_dict = dict(verdict)
        evidence_parts.append(f"### Quality Verdict\nScore: {verdict_dict.get('score', 'N/A')}/100\nCategory: {verdict_dict.get('category', 'N/A')}\nFlags: {verdict_dict.get('flags', 'None')}")
        for key in ['revenue_score', 'margin_score', 'leverage_score', 'wc_score', 'roce_score', 'evolution_score']:
            val = verdict_dict.get(key)
            if val is not None:
                evidence_parts.append(f"- {key}: {val}/10")

    if mri:
        mri_dict = dict(mri)
        score = mri_dict.get('total_score')
        evidence_parts.append(f"\n### MRI Technical Score\nTotal: {score}/100")
        for cond in ['condition_ema_50_200', 'condition_ema_200_slope', 'condition_6m_high', 'condition_volume', 'condition_rs', 'condition_breakout_10d', 'condition_price_quality']:
            val = mri_dict.get(cond)
            if val is not None:
                evidence_parts.append(f"- {cond}: {'PASS' if val else 'FAIL'}")

    if history:
        evidence_parts.append(f"\n### Financial History ({len(history)} years)")
        for row in history:
            evidence_parts.append(f"Year {row['year']}: Rev={row['revenue']}, EBITDA={row['ebitda']}, Profit={row['net_profit']}, Debt={row['debt']}, Equity={row['equity']}")

    evidence = "\n".join(evidence_parts)
    user_message = f"Analyze this company ({symbol}):\n\n{evidence}"

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": DEBATE_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        content = resp.choices[0].message.content
        result = json.loads(content)
        result["symbol"] = symbol
        return result
    except Exception as e:
        logger.error(f"Debate GPT call failed for {symbol}: {e}")
        return {"error": f"GPT analysis failed: {e}"}

def format_debate_email_html(analysis):
    symbol = analysis.get("symbol", "Unknown")
    verdict = analysis.get("verdict", {})
    rec = verdict.get("buy_recommendation", "HOLD")
    rec_color = {"BUY": "#22c55e", "HOLD": "#eab308", "AVOID": "#ef4444"}.get(rec, "#94a3b8")

    nuances = "".join(f"<li>{n}</li>" for n in analysis.get("nuances", []))
    mistakes = "".join(f"<li>{m}</li>" for m in analysis.get("glaring_mistakes", []))

    return f"""
    <html>
    <body style="font-family:sans-serif;max-width:650px;margin:auto;padding:20px;color:#1e293b">
        <div style="border:2px solid {rec_color};border-radius:16px;padding:24px">
            <div style="text-align:center;margin-bottom:20px">
                <h1 style="margin:0;font-size:28px">{symbol}</h1>
                <div style="display:inline-block;margin-top:8px;padding:4px 16px;border-radius:20px;background:{rec_color};color:white;font-weight:bold;font-size:14px">
                    {rec}
                </div>
                <div style="margin-top:8px;font-size:32px;font-weight:900;color:{rec_color}">{verdict.get("score", "?")}/10</div>
            </div>

            <div style="background:#f8fafc;border-radius:12px;padding:16px;margin:16px 0">
                <h3 style="margin:0 0 8px 0;color:#334155">📊 Guidance vs Reality</h3>
                <p style="margin:0;color:#475569;line-height:1.5">{analysis.get("guidance_vs_reality", "No analysis.")}</p>
            </div>

            {f'<div style="background:#fefce8;border-radius:12px;padding:16px;margin:16px 0"><h3 style="margin:0 0 8px 0;color:#a16207">🔍 Nuances</h3><ul style="margin:0;color:#854d0e;line-height:1.6">{nuances}</ul></div>' if analysis.get("nuances") else ""}

            {f'<div style="background:#fef2f2;border-radius:12px;padding:16px;margin:16px 0"><h3 style="margin:0 0 8px 0;color:#991b1b">⚠️ Glaring Mistakes</h3><ul style="margin:0;color:#7f1d1d;line-height:1.6">{mistakes}</ul></div>' if analysis.get("glaring_mistakes") else ""}

            {f'<div style="background:#f0fdf4;border-radius:12px;padding:16px;margin:16px 0"><h3 style="margin:0 0 8px 0;color:#166534">💡 What Would Change My Mind</h3><p style="margin:0;color:#14532d;line-height:1.5">{verdict.get("would_change_my_mind", "Not specified.")}</p></div>' if verdict.get("would_change_my_mind") else ""}

            <hr style="border:1px solid #e2e8f0;margin:20px 0">
            <p style="font-size:11px;color:#94a3b8;text-align:center">Generated by MRI Debater | Quality Investor Framework</p>
        </div>
    </body>
    </html>
    """