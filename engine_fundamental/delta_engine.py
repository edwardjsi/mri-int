import pandas as pd
import logging
from engine_core.db import get_connection, fetch_df

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def compute_structural_deltas(symbol):
    """
    Compute Q-on-Q and Y-on-Y deltas for key quarterly metrics.
    Detects margin expansion, revenue acceleration, and ROCE shifts.
    """
    # Fetch last 8 quarters to compute deltas and Y-on-Y
    query = """
        SELECT year, quarter, revenue, gross_profit, ebitda, 
               operating_income, net_profit, eps, cfo, capex
        FROM aae_quarterly_financials
        WHERE symbol = %s
        ORDER BY year DESC, quarter DESC
        LIMIT 8
    """
    df = fetch_df(query, (symbol.upper(),))

    if df.empty or len(df) < 2:
        logger.warning(f"Insufficient quarterly data for delta analysis: {symbol}")
        return None

    # Ensure numeric types (fetch_df might return Decimals)
    for col in ['revenue', 'ebitda', 'gross_profit', 'operating_income', 'net_profit', 'eps']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Reverse to chronological order for delta computation
    df = df.iloc[::-1].reset_index(drop=True)

    # Compute QoQ Deltas
    df['rev_qoq'] = df['revenue'].pct_change()
    df['ebitda_qoq'] = df['ebitda'].pct_change()
    df['margin_qoq'] = (df['ebitda'] / df['revenue']).diff()
    
    # Compute YoY Deltas (if at least 5 quarters exist)
    if len(df) >= 5:
        df['rev_yoy'] = df['revenue'].pct_change(4)
        df['ebitda_yoy'] = df['ebitda'].pct_change(4)
        df['margin_yoy'] = (df['ebitda'] / df['revenue']).diff(4)
    else:
        df['rev_yoy'] = None
        df['ebitda_yoy'] = None
        df['margin_yoy'] = None

    # Return the latest quarter's delta snapshot
    latest = df.iloc[-1].to_dict()
    
    # Logic for Structural Inflection Detection
    inflection = False
    reasons = []
    
    if latest.get('margin_qoq') and latest['margin_qoq'] > 0.02: # 200bps expansion
        inflection = True
        reasons.append(f"Margin Expansion QoQ: {latest['margin_qoq']*100:.1f}bps")
    
    if latest.get('rev_qoq') and latest['rev_qoq'] > 0.10: # 10% QoQ growth
        inflection = True
        reasons.append(f"Revenue Acceleration QoQ: {latest['rev_qoq']*100:.1f}%")

    if latest.get('rev_yoy') and latest['rev_yoy'] > 0.20: # 20% YoY growth
        inflection = True
        reasons.append(f"Strong YoY Growth: {latest['rev_yoy']*100:.1f}%")

    return {
        "symbol": symbol,
        "year": latest['year'],
        "quarter": latest['quarter'],
        "inflection": inflection,
        "reasons": reasons,
        "metrics": latest
    }

if __name__ == "__main__":
    # Test with TCS
    deltas = compute_structural_deltas("TCS")
    print(deltas)
