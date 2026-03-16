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
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        nse_res = requests.get("https://archives.nseindia.com/content/equities/EQUITY_L.csv", headers=headers, timeout=15)
        nse_df = pd.read_csv(io.StringIO(nse_res.text))
        bse_res = requests.get("https://www.bseindia.com/downloads1/List_of_companies.csv", headers=headers, timeout=15)
        bse_df = pd.read_csv(io.StringIO(bse_res.text))
        merged = pd.merge(
            nse_df[['SYMBOL', 'ISIN NUMBER']].rename(columns={'ISIN NUMBER': 'ISIN'}),
            bse_df[['Security Code', 'ISIN No']].rename(columns={'ISIN No': 'ISIN'}),
            on='ISIN', how='inner'
        )
        d = dict(zip(merged['SYMBOL'].str.strip(), merged['Security Code'].astype(str).str.strip()))
        d.update({"CIGNITITEC": "534756", "LUMAXTECH": "532796", "ONEGLOBAL": "512527", "SHILCTECH": "532888", "AGI": "500187", "SKFINDIA": "500474"})
        return d
    except Exception: return {}

def ingest_missing_symbols_sync(missing_symbols: list, original_holdings: list, client_id: str, email: str, name: str):
    logger.info(f"[INGEST] Running wholesome tiered search for {len(missing_symbols)} symbols.")
    translator = build_symbol_translator()
    start_date = (datetime.today() - timedelta(days=365 * 3)).strftime('%Y-%m-%d')
    end_date = datetime.today().strftime('%Y-%m-%d')
    inserted_any = False

    for symbol in missing_symbols:
        sym = symbol.upper().strip().split('.')[0]
        safe_term = translator.get(sym, sym)
        
        search_list = [f"{safe_term}.BO", f"{sym}.NS", f"{sym}.BO"] if safe_term.isdigit() else [f"{sym}.NS", f"{sym}.BO"]
        
        df = pd.DataFrame()
        for t in search_list:
            try:
                raw = yf.download(t, start=start_date, end=end_date, progress=False, auto_adjust=True)
                if not raw.empty:
                    df = raw.reset_index()
                    if isinstance(df.columns, pd.MultiIndex): df.columns = [c[0] for c in df.columns]
                    df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]
                    break
            except Exception: continue

        if not df.empty:
            df["symbol"] = symbol
            df["adjusted_close"] = df.get("adj_close", df.get("close"))
            df["date"] = pd.to_datetime(df["date"]).dt.date
            for col in ["open", "high", "low"]:
                if col not in df.columns: df[col] = df["close"]
            try:
                insert_daily_prices(df[["symbol", "date", "open", "high", "low", "close", "adjusted_close", "volume"]].to_dict("records"))
                inserted_any = True
            except Exception: continue

    if inserted_any:
        add_indicator_columns_if_missing()
        data_df, idx_df = fetch_data_for_symbols(missing_symbols)
        if data_df is not None and not data_df.empty:
            updates = compute_indicators(data_df, idx_df)
            if updates: update_db_with_indicators(updates)
        create_market_regime_and_scores_tables()
        compute_market_regime()
        compute_stock_scores_for_symbols(missing_symbols)
        
    conn = get_connection()
    report = analyze_portfolio(original_holdings, conn=conn)
    send_portfolio_review_email(email, name, report)
    conn.close()

def send_portfolio_review_email(email: str, name: str, report: dict):
    import os
    from src.aws_ses import get_ses_client, resolve_ses_region
    sender = os.getenv("SES_SENDER_EMAIL", "edwardjsi@gmail.com")
    ses = get_ses_client(resolve_ses_region())
    subject = f"MRI Risk Audit: {report.get('risk_level')} Risk"
    rows = "".join([f"<tr><td style='padding:8px;border-bottom:1px solid #eee;'>{h['symbol']}</td><td style='padding:8px;border-bottom:1px solid #eee;'>{h['score'] if h['score'] is not None else 'N/A'}/5</td><td style='padding:8px;border-bottom:1px solid #eee;'>{h['alignment']}</td></tr>" for h in report.get('holdings', [])])
    html = f"<html><body><h3>Hi {name}, your Risk Audit is ready.</h3><table style='width:100%;'>{rows}</table></body></html>"
    try:
        ses.send_email(Source=sender, Destination={"ToAddresses": [email]}, Message={"Subject": {"Data": subject}, "Body": {"Html": {"Data": html}}})
    except Exception: pass