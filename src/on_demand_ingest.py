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
    """Builds an in-memory dictionary mapping NSE Symbols to BSE Numeric Codes via ISIN."""
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        nse_url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
        nse_res = requests.get(nse_url, headers=headers, timeout=15)
        nse_df = pd.read_csv(io.StringIO(nse_res.text))
        nse_df.columns = nse_df.columns.str.strip()
        nse_map = nse_df[['SYMBOL', 'ISIN NUMBER']].rename(columns={'ISIN NUMBER': 'ISIN'})

        bse_url = "https://www.bseindia.com/downloads1/List_of_companies.csv"
        bse_res = requests.get(bse_url, headers=headers, timeout=15)
        bse_df = pd.read_csv(io.StringIO(bse_res.text))
        bse_df.columns = bse_df.columns.str.strip()
        bse_map = bse_df[['Security Code', 'ISIN No']].rename(columns={'ISIN No': 'ISIN'})

        merged = pd.merge(nse_map, bse_map, on='ISIN', how='inner')
        return dict(zip(merged['SYMBOL'].str.strip(), merged['Security Code'].astype(str).str.strip()))
    except Exception as e:
        logger.warning(f"[INGEST] Failed to build ISIN bridge: {e}")
        return {}

def grade_symbols_sync(
    symbols: list[str],
    original_holdings: list | None = None,
    email: str | None = None,
    name: str | None = None,
    send_email: bool = False,
):
    """Background task: compute indicators + stock scores for already-downloaded symbols."""
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

        report = None
        if original_holdings:
            conn = None
            try:
                conn = get_connection()
                report = analyze_portfolio(original_holdings, conn=conn)
            except Exception: pass
            finally:
                if conn: conn.close()

        if send_email and email and report:
            try: send_portfolio_review_email(email, name or "", report)
            except Exception: pass

    except Exception as e:
        logger.error(f"[GRADE] Grading failed: {e}")

def _flatten_yfinance_columns(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    df = df.reset_index()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0].lower().replace(" ", "_") if col[1] == "" or col[1] == symbol
                      else col[0].lower().replace(" ", "_") for col in df.columns]
    else:
        df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]
    df = df.loc[:, ~df.columns.duplicated()]
    return df

def ingest_missing_symbols_sync(missing_symbols: list, original_holdings: list, client_id: str, email: str, name: str):
    """Background task: downloads historical data for missing symbols, processes, and emails report."""
    logger.info(f"[INGEST] Starting background ingestion for {len(missing_symbols)} missing symbols.")
    
    translator = build_symbol_translator()

    end_dt = datetime.today()
    end_date = end_dt.strftime('%Y-%m-%d')
    start_date = (end_dt - timedelta(days=365 * 3)).strftime('%Y-%m-%d')

    inserted_any = False

    for symbol in missing_symbols:
        df = pd.DataFrame()
        user_symbol = symbol.upper().strip()

        if user_symbol.endswith(".NS") or user_symbol.endswith(".BO"): user_symbol = user_symbol[:-3]
        if user_symbol.startswith("BOM") and user_symbol[3:].isdigit(): user_symbol = user_symbol[3:]

        # Bridge translation
        safe_search_term = translator.get(user_symbol, user_symbol)
        
        if safe_search_term.isdigit():
            primary, secondary = f"{safe_search_term}.BO", f"{safe_search_term}.NS"
        else:
            primary, secondary = f"{safe_search_term}.NS", f"{safe_search_term}.BO"

        try:
            raw = yf.download(primary, start=start_date, end=end_date, progress=False, auto_adjust=True)
            if raw is not None and not raw.empty: df = _flatten_yfinance_columns(raw, primary)
        except Exception: pass

        if df.empty:
            try:
                raw = yf.download(secondary, start=start_date, end=end_date, progress=False, auto_adjust=True)
                if raw is not None and not raw.empty: df = _flatten_yfinance_columns(raw, secondary)
            except Exception: pass

        if df.empty:
            logger.error(f"[INGEST] No data found for {user_symbol}.")
            continue

        if "close" not in df.columns and "adj_close" in df.columns:
            df["close"] = df["adj_close"]
            
        if "close" not in df.columns: continue

        for col in ["open", "high", "low"]:
            if col not in df.columns: df[col] = df["close"]
        if "volume" not in df.columns: df["volume"] = 0

        df["adjusted_close"] = df.get("adj_close", df["close"])
        df["date"] = pd.to_datetime(df["date"]).dt.date
        
        # Save explicitly as the user's requested string
        df["symbol"] = user_symbol 
        df = df[["symbol", "date", "open", "high", "low", "close", "adjusted_close", "volume"]].dropna(subset=["close"])

        if not df.empty:
            try:
                records = df.to_dict("records")
                insert_daily_prices(records)
                inserted_any = True
                logger.info(f"[INGEST] ✅ Inserted {len(records)} rows for {user_symbol}.")
            except Exception as e:
                logger.error(f"[INGEST] DB insert failed for {user_symbol}: {e}")

    if inserted_any:
        try:
            add_indicator_columns_if_missing()
            data_df, idx_df = fetch_data_for_symbols(missing_symbols)
            if data_df is not None and not data_df.empty:
                updates = compute_indicators(data_df, idx_df)
                if updates: update_db_with_indicators(updates)
            
            create_market_regime_and_scores_tables()
            try: compute_market_regime()
            except Exception: pass
            compute_stock_scores_for_symbols(missing_symbols)
        except Exception as e:
            logger.error(f"[INGEST] Engine triggers failed: {e}")

    final_report = None
    conn = None
    try:
        conn = get_connection()
        final_report = analyze_portfolio(original_holdings, conn=conn)
    except Exception as e:
        logger.error(f"[INGEST] Final report generation failed: {e}")
    finally:
        if conn: conn.close()

    if final_report:
        try: send_portfolio_review_email(email, name, final_report)
        except Exception as e: logger.error(f"[INGEST] Email send failed: {e}")

def send_portfolio_review_email(email: str, name: str, report: dict):
    """Formats and sends the final Risk Audit report via AWS SES."""
    import os
    from src.aws_ses import aws_credentials_present, get_ses_client, resolve_ses_region

    SENDER_EMAIL = os.getenv("SES_SENDER_EMAIL", "edwardjsi@gmail.com")

    if not aws_credentials_present(): return False

    try: ses_region = resolve_ses_region()
    except Exception: return False

    ses = get_ses_client(ses_region)

    subject = f"Your Portfolio Risk Audit is Ready: {report.get('risk_level', 'N/A')} Risk"
    regime_color = {"BULL": "#22c55e", "BEAR": "#ef4444", "NEUTRAL": "#f59e0b"}.get(report.get('regime', ''), "#6b7280")
    risk_color = {"LOW": "#22c55e", "MODERATE": "#eab308", "HIGH": "#ef4444", "EXTREME": "#ef4444"}.get(report.get('risk_level', ''), "#6b7280")

    holding_rows = ""
    for h in report.get('holdings', []):
        score_str = f"{h['score']}/5" if h.get('score') is not None else "N/A"
        ema_str = "⚠️ YES" if h.get('below_200ema') else "NO"
        holding_rows += f"""
        <tr>
            <td style="padding:8px;border-bottom:1px solid #e5e7eb;font-weight:600">{h['symbol']}</td>
            <td style="padding:8px;border-bottom:1px solid #e5e7eb">{score_str}</td>
            <td style="padding:8px;border-bottom:1px solid #e5e7eb">{h.get('alignment','N/A')}</td>
            <td style="padding:8px;border-bottom:1px solid #e5e7eb">{h.get('weight_pct','?')}%</td>
            <td style="padding:8px;border-bottom:1px solid #e5e7eb;color:{'#ef4444' if h.get('below_200ema') else '#6b7280'}">{ema_str}</td>
        </tr>"""

    html_body = f"""
    <html>
    <body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:600px;margin:0 auto;padding:20px;background:#f9fafb">
        <div style="background:white;border-radius:12px;padding:24px;box-shadow:0 1px 3px rgba(0,0,0,0.1)">
            <h1 style="margin:0 0 16px;font-size:20px;color:#111827">🛡️ Your Requested Risk Audit</h1>
            <p style="color:#374151">Hi {name},</p>
            <p style="color:#374151;margin-bottom:24px">Your portfolio contains {len(report.get('holdings', []))} holdings. Here is the final MRI diagnosis.</p>

            <div style="display:flex;gap:12px;margin-bottom:20px">
                <div style="flex:1;background:{risk_color}15;border-left:4px solid {risk_color};padding:12px;border-radius:4px">
                    <span style="font-size:13px;color:#6b7280">Overall Risk</span>
                    <div style="font-size:18px;font-weight:700;color:{risk_color}">{report.get('risk_level','N/A')}</div>
                    <div style="font-size:12px;color:#6b7280">Score: {report.get('risk_score_pct','?')}</div>
                </div>
                <div style="flex:1;background:{regime_color}15;border-left:4px solid {regime_color};padding:12px;border-radius:4px">
                    <span style="font-size:13px;color:#6b7280">Market Regime</span>
                    <div style="font-size:18px;font-weight:700;color:{regime_color}">{report.get('regime','N/A')}</div>
                </div>
            </div>

            <h2 style="color:#1e293b;font-size:16px;margin:20px 0 8px">Holding Breakdown</h2>
            <table style="width:100%;border-collapse:collapse;font-size:13px">
                <tr style="background:#f8fafc">
                    <th style="padding:8px;text-align:left;color:#475569">Symbol</th>
                    <th style="padding:8px;text-align:left;color:#475569">Score</th>
                    <th style="padding:8px;text-align:left;color:#475569">Alignment</th>
                    <th style="padding:8px;text-align:left;color:#475569">Weight</th>
                    <th style="padding:8px;text-align:left;color:#475569">&lt; 200 EMA</th>
                </tr>
                {holding_rows}
            </table>
        </div>
    </body>
    </html>"""

    try:
        ses.send_email(
            Source=SENDER_EMAIL,
            Destination={"ToAddresses": [email]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {"Html": {"Data": html_body, "Charset": "UTF-8"}},
            },
        )
        return True
    except Exception: return False