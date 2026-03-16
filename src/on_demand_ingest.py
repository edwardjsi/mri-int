# src/on_demand_ingest.py
import logging
import yfinance as yf
import pandas as pd
import requests
import io
from datetime import datetime, timedelta
from src.db import get_connection, insert_daily_prices
from src.indicator_engine import fetch_data_for_symbols, compute_indicators, update_db_with_indicators, add_indicator_columns_if_missing
from src.regime_engine import create_market_regime_and_scores_tables, compute_market_regime, compute_stock_scores_for_symbols
from src.portfolio_review_engine import analyze_portfolio

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def build_symbol_translator() -> dict:
    """Builds exhaustive mapping including manual overrides."""
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        # NSE
        nse_url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
        nse_res = requests.get(nse_url, headers=headers, timeout=15)
        nse_df = pd.read_csv(io.StringIO(nse_res.text))
        nse_df.columns = nse_df.columns.str.strip()
        nse_map = nse_df[['SYMBOL', 'ISIN NUMBER']].rename(columns={'ISIN NUMBER': 'ISIN'})

        # BSE
        bse_url = "https://www.bseindia.com/downloads1/List_of_companies.csv"
        bse_res = requests.get(bse_url, headers=headers, timeout=15)
        bse_df = pd.read_csv(io.StringIO(bse_res.text))
        bse_df.columns = bse_df.columns.str.strip()
        bse_map = bse_df[['Security Code', 'ISIN No']].rename(columns={'ISIN No': 'ISIN'})

        merged = pd.merge(nse_map, bse_map, on='ISIN', how='inner')
        translator = dict(zip(merged['SYMBOL'].str.strip(), merged['Security Code'].astype(str).str.strip()))
        
        # Hard overrides for specific portfolio names
        translator.update({
            "CIGNITITEC": "534756", "LUMAXTECH": "532796", 
            "SKFINDIA": "500474", "AGI": "500187"
        })
        return translator
    except Exception as e:
        logger.warning(f"[INGEST] Bridge Build Error: {e}")
        return {}

def grade_symbols_sync(symbols: list[str], original_holdings: list | None = None, email: str | None = None, name: str | None = None, send_email: bool = False):
    symbols_clean = [str(s).upper().strip() for s in (symbols or []) if str(s).strip()]
    if not symbols_clean: return
    try:
        add_indicator_columns_if_missing()
        data_df, idx_df = fetch_data_for_symbols(symbols_clean)
        if data_df is not None and not data_df.empty:
            updates = compute_indicators(data_df, idx_df)
            if updates: update_db_with_indicators(updates)
        create_market_regime_and_scores_tables()
        try: compute_market_regime()
        except Exception: pass
        compute_stock_scores_for_symbols(symbols_clean)
        if original_holdings and send_email and email:
            conn = get_connection()
            report = analyze_portfolio(original_holdings, conn=conn)
            send_portfolio_review_email(email, name or "", report)
            conn.close()
    except Exception as e: logger.error(f"[GRADE] Failed: {e}")

def _flatten_yf(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    df = df.reset_index()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0].lower().replace(" ", "_") if col[1] == "" or col[1] == symbol else col[0].lower().replace(" ", "_") for col in df.columns]
    else:
        df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]
    return df.loc[:, ~df.columns.duplicated()]

def ingest_missing_symbols_sync(missing_symbols: list, original_holdings: list, client_id: str, email: str, name: str):
    logger.info(f"[INGEST] Processing {len(missing_symbols)} missing symbols.")
    translator = build_symbol_translator()
    end_date = datetime.today().strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=365 * 3)).strftime('%Y-%m-%d')
    inserted_any = False

    for symbol in missing_symbols:
        user_sym = symbol.upper().strip()
        safe_term = translator.get(user_sym, user_sym)
        
        # Smart route: try BSE numeric first if available
        search_terms = [f"{safe_term}.BO", f"{safe_term}.NS"] if safe_term.isdigit() else [f"{safe_term}.NS", f"{safe_term}.BO"]
        
        df = pd.DataFrame()
        for term in search_terms:
            try:
                raw = yf.download(term, start=start_date, end=end_date, progress=False, auto_adjust=True)
                if raw is not None and not raw.empty:
                    df = _flatten_yf(raw, term)
                    break
            except Exception: continue

        if not df.empty:
            df["symbol"] = user_sym # Use original string
            df["adjusted_close"] = df.get("adj_close", df.get("close"))
            df["date"] = pd.to_datetime(df["date"]).dt.date
            for col in ["open", "high", "low"]:
                if col not in df.columns: df[col] = df["close"]
            df = df[["symbol", "date", "open", "high", "low", "close", "adjusted_close", "volume"]].dropna(subset=["close"])
            try:
                insert_daily_prices(df.to_dict("records"))
                inserted_any = True
            except Exception: continue

    if inserted_any:
        grade_symbols_sync(missing_symbols, original_holdings, email, name, send_email=True)

def send_portfolio_review_email(email: str, name: str, report: dict):
    import os
    from src.aws_ses import get_ses_client, resolve_ses_region
    sender = os.getenv("SES_SENDER_EMAIL", "edwardjsi@gmail.com")
    ses = get_ses_client(resolve_ses_region())
    
    subject = f"Your Portfolio Risk Audit: {report.get('risk_level')} Risk"
    risk_color = {"LOW": "#22c55e", "MODERATE": "#eab308", "HIGH": "#ef4444", "EXTREME": "#ef4444"}.get(report.get('risk_level'), "#6b7280")
    
    rows = "".join([f"<tr><td style='padding:8px;border-bottom:1px solid #eee;'>{h['symbol']}</td><td style='padding:8px;border-bottom:1px solid #eee;'>{h['score']}/5</td><td style='padding:8px;border-bottom:1px solid #eee;'>{h['alignment']}</td></tr>" for h in report.get('holdings', [])])
    
    html = f"<html><body style='font-family:sans-serif;padding:20px;'><div style='background:white;padding:24px;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,0.1);'><h2>Risk Audit Results</h2><div style='background:{risk_color}15;padding:12px;border-left:4px solid {risk_color};margin-bottom:20px;'><strong>Risk Level: {report.get('risk_level')}</strong></div><table style='width:100%;border-collapse:collapse;'>{rows}</table></div></body></html>"
    
    try:
        ses.send_email(Source=sender, Destination={"ToAddresses": [email]}, Message={"Subject": {"Data": subject}, "Body": {"Html": {"Data": html}}})
        return True
    except Exception: return False