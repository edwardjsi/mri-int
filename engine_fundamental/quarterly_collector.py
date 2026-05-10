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

def fetch_and_store_quarterly(symbol):
    """
    Fetch quarterly financials from Yahoo and store in aae_quarterly_financials table.
    """
    if symbol.endswith(".NS") or symbol.endswith(".BO"):
        yf_sym = symbol
    elif symbol.isdigit():
        yf_sym = f"{symbol}.BO"
    else:
        yf_sym = f"{symbol}.NS"

    base_sym = symbol.replace(".NS", "").replace(".BO", "").upper()
    
    logger.info(f"Fetching quarterly data for {yf_sym}...")
    stock = yf.Ticker(yf_sym)
    
    try:
        q_income = stock.quarterly_financials.T
        q_balance = stock.quarterly_balance_sheet.T
        q_cashflow = stock.quarterly_cashflow.T
    except Exception as e:
        logger.error(f"Failed to fetch quarterly data for {yf_sym}: {e}")
        return None

    if q_income.empty:
        logger.warning(f"No quarterly income statement found for {yf_sym}")
        return None

    conn = get_connection()
    cur = conn.cursor()
    
    records_saved = 0
    for date_idx, row in q_income.iterrows():
        year = date_idx.year
        quarter = (date_idx.month - 1) // 3 + 1
        
        # Match balance sheet and cashflow by date
        # yfinance index is usually the same for all statements
        bs_row = q_balance.loc[date_idx] if date_idx in q_balance.index else pd.Series()
        cf_row = q_cashflow.loc[date_idx] if date_idx in q_cashflow.index else pd.Series()

        # Extract values
        revenue = sanitize_val(row.get('Total Revenue'))
        gross_profit = sanitize_val(row.get('Gross Profit'))
        ebitda = sanitize_val(row.get('EBITDA'))
        operating_income = sanitize_val(row.get('Operating Income'))
        net_profit = sanitize_val(row.get('Net Income'))
        eps = sanitize_val(row.get('Basic EPS')) or sanitize_val(row.get('Diluted EPS'))
        
        total_assets = sanitize_val(bs_row.get('Total Assets'))
        total_liabilities = sanitize_val(bs_row.get('Total Liabilities Net Minority Interest'))
        current_assets = sanitize_val(bs_row.get('Current Assets'))
        current_liabilities = sanitize_val(bs_row.get('Current Liabilities'))
        inventory = sanitize_val(bs_row.get('Inventory'))
        receivables = sanitize_val(bs_row.get('Accounts Receivable'))
        
        debt_raw = (bs_row.get('Current Debt', 0) or 0) + (bs_row.get('Long Term Debt', 0) or 0)
        debt = sanitize_val(debt_raw)
        equity = sanitize_val(bs_row.get('Stockholders Equity'))
        
        cfo = sanitize_val(cf_row.get('Operating Cash Flow'))
        capex = sanitize_val(cf_row.get('Capital Expenditure'))

        cur.execute("""
            INSERT INTO public.aae_quarterly_financials (
                symbol, year, quarter, revenue, gross_profit, ebitda, 
                operating_income, net_profit, eps, total_assets, 
                total_liabilities, current_assets, current_liabilities, 
                inventory, receivables, debt, equity, cfo, capex
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (symbol, year, quarter) DO UPDATE SET
                revenue = EXCLUDED.revenue,
                gross_profit = EXCLUDED.gross_profit,
                ebitda = EXCLUDED.ebitda,
                operating_income = EXCLUDED.operating_income,
                net_profit = EXCLUDED.net_profit,
                eps = EXCLUDED.eps,
                total_assets = EXCLUDED.total_assets,
                total_liabilities = EXCLUDED.total_liabilities,
                current_assets = EXCLUDED.current_assets,
                current_liabilities = EXCLUDED.current_liabilities,
                inventory = EXCLUDED.inventory,
                receivables = EXCLUDED.receivables,
                debt = EXCLUDED.debt,
                equity = EXCLUDED.equity,
                cfo = EXCLUDED.cfo,
                capex = EXCLUDED.capex,
                updated_at = NOW()
        """, (
            base_sym, year, quarter, revenue, gross_profit, ebitda,
            operating_income, net_profit, eps, total_assets,
            total_liabilities, current_assets, current_liabilities,
            inventory, receivables, debt, equity, cfo, capex
        ))
        records_saved += 1

    conn.commit()
    cur.close()
    conn.close()
    logger.info(f"Stored {records_saved} quarters of financial data for {base_sym}")
    return records_saved

if __name__ == "__main__":
    # Test with a major symbol
    fetch_and_store_quarterly("TCS.NS")
