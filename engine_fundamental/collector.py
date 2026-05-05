import numpy as np
import yfinance as yf
import logging
import pandas as pd
from engine_core.db import get_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def sanitize_val(val):
    """Convert numpy/pandas types to native Python types for SQL compatibility."""
    if val is None or (isinstance(val, (float, int)) and np.isnan(val)):
        return None
    if hasattr(val, 'item'):
        return val.item()
    return val

def fetch_and_store_financials(symbol):
    """
    Fetch 5-10 years of financials from Yahoo and store in fundamental_financials table.
    Ensures symbol is normalized (base MRI format) in the database.
    """
    # Logic for determining Yahoo Symbol
    if symbol.endswith(".NS") or symbol.endswith(".BO"):
        yf_sym = symbol
    elif symbol.isdigit():
        yf_sym = f"{symbol}.BO"
    else:
        yf_sym = f"{symbol}.NS"

    base_sym = symbol.replace(".NS", "").replace(".BO", "").upper()
    
    logger.info(f"Fetching fundamental data for {yf_sym} (Database: {base_sym})...")
    stock = yf.Ticker(yf_sym)
    
    # Fallback check: if financials are empty, try the other exchange if it's a string symbol
    try:
        income = stock.financials.T
        if income.empty and not symbol.isdigit() and ".NS" in yf_sym:
            alt_sym = yf_sym.replace(".NS", ".BO")
            logger.info(f"Empty results for {yf_sym}, trying fallback {alt_sym}...")
            stock = yf.Ticker(alt_sym)
            income = stock.financials.T
            yf_sym = alt_sym
        
        # Now fetch balance sheet
        balance = stock.balance_sheet.T
    except Exception as e:
        logger.error(f"Failed to fetch data for {yf_sym}: {e}")
        return None

    if income.empty or balance.empty:
        logger.warning(f"No financial statements found for {yf_sym}")
        return None

    conn = get_connection()
    cur = conn.cursor()
    
    records_saved = 0
    for date_idx, row in income.iterrows():
        year = date_idx.year
        
        # Balance sheet date might slightly differ or have extra/missing rows
        # We try to find the matching year in balance sheet
        bs_row = balance[balance.index.year == year]
        if bs_row.empty:
            # Fallback to nearest date if exact year match fails
            bs_row = balance.iloc[(balance.index - date_idx).abs().argmin()]
        else:
            bs_row = bs_row.iloc[0]

        # Extract values with safe defaults
        revenue = sanitize_val(row.get('Total Revenue'))
        ebitda = sanitize_val(row.get('EBITDA'))
        net_profit = sanitize_val(row.get('Net Income'))
        
        total_assets = sanitize_val(bs_row.get('Total Assets'))
        receivables = sanitize_val(bs_row.get('Net Receivables'))
        inventory = sanitize_val(bs_row.get('Inventory'))
        debt_raw = (bs_row.get('Short Long Term Debt', 0) or 0) + (bs_row.get('Long Term Debt', 0) or 0)
        debt = sanitize_val(debt_raw)
        equity = sanitize_val(bs_row.get('Total Stockholder Equity'))
        
        # Capital Employed = Total Assets - Current Liabilities (approximation)
        # Or Total Assets - Receivables as a lean proxy if CL is missing
        capital_employed = None
        if total_assets is not None:
            capital_employed = total_assets - (receivables or 0)

        cur.execute("""
            INSERT INTO public.fundamental_financials (
                symbol, year, revenue, ebitda, net_profit, total_assets, 
                capital_employed, receivables, inventory, debt, equity
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (symbol, year) DO UPDATE SET
                revenue = EXCLUDED.revenue,
                ebitda = EXCLUDED.ebitda,
                net_profit = EXCLUDED.net_profit,
                total_assets = EXCLUDED.total_assets,
                capital_employed = EXCLUDED.capital_employed,
                receivables = EXCLUDED.receivables,
                inventory = EXCLUDED.inventory,
                debt = EXCLUDED.debt,
                equity = EXCLUDED.equity,
                updated_at = NOW()
        """, (
            base_sym, year, revenue, ebitda, net_profit, total_assets,
            capital_employed, receivables, inventory, debt, equity
        ))
        records_saved += 1

    conn.commit()
    cur.close()
    conn.close()
    logger.info(f"Stored {records_saved} years of financial data for {base_sym}")
    return records_saved

if __name__ == "__main__":
    # Test with a major symbol
    fetch_and_store_financials("RELIANCE.NS")
