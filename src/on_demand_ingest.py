import logging
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from src.db import get_connection, insert_daily_prices
from src.indicator_engine import fetch_data_for_symbols, compute_indicators, update_db_with_indicators, add_indicator_columns_if_missing
from src.regime_engine import create_market_regime_and_scores_tables, compute_stock_scores
from src.portfolio_review_engine import analyze_portfolio

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def grade_symbols_sync(symbols: list[str], original_holdings: list | None = None):
    """
    Background task: compute indicators + stock scores for the given symbols only.
    This is used to (re)grade persisted Digital Twin holdings without re-uploading CSVs.
    """
    symbols_clean = [str(s).upper().strip() for s in (symbols or []) if str(s).strip()]
    if not symbols_clean:
        logger.info("[GRADE] No symbols provided; skipping.")
        return

    logger.info(f"[GRADE] Starting grading for {len(symbols_clean)} symbol(s): {symbols_clean}")

    try:
        add_indicator_columns_if_missing()
        data_df, idx_df = fetch_data_for_symbols(symbols_clean)
        if data_df is not None and not data_df.empty:
            updates = compute_indicators(data_df, idx_df)
            if updates:
                update_db_with_indicators(updates)
                logger.info(f"[GRADE] Indicator engine: {len(updates)} row(s) updated.")

        create_market_regime_and_scores_tables()
        compute_stock_scores()
        logger.info("[GRADE] Stock score engine complete.")

        if original_holdings:
            conn = None
            try:
                conn = get_connection()
                report = analyze_portfolio(original_holdings, conn=conn)
                logger.info(f"[GRADE] Re-analysis complete: {report.get('risk_level')} risk.")
            except Exception as e:
                logger.warning(f"[GRADE] Re-analysis failed: {e}")
            finally:
                if conn:
                    conn.close()

    except Exception as e:
        logger.error(f"[GRADE] Grading failed: {e}")
    finally:
        logger.info("[GRADE] Grading pipeline finished.")


def _flatten_yfinance_columns(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """
    yfinance returns a MultiIndex dataframe like ('Close', 'RELIANCE.NS').
    This flattens it to simple lowercase column names: 'close', 'open', etc.
    Also handles the rare flat-column case for a single ticker.
    """
    df = df.reset_index()

    if isinstance(df.columns, pd.MultiIndex):
        # For multi-ticker downloads, drop the ticker level and keep the stat level
        df.columns = [col[0].lower().replace(" ", "_") if col[1] == "" or col[1] == symbol
                      else col[0].lower().replace(" ", "_")
                      for col in df.columns]
    else:
        df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]

    # De-duplicate columns that may have collapsed (yfinance quirk)
    df = df.loc[:, ~df.columns.duplicated()]
    return df


def ingest_missing_symbols_sync(
    missing_symbols: list,
    original_holdings: list,
    client_id: str,
    email: str,
    name: str
):
    """
    Background task: downloads historical data for missing symbols via yfinance,
    computes their indicators + stock scores, then emails the completed Risk Audit.

    Tries NSE (.NS) first, falls back to BSE (.BO).
    Fetches 2 years of data to ensure EMA-200 can be computed reliably.
    """
    logger.info(f"[INGEST] Starting background ingestion for {len(missing_symbols)} symbol(s): {missing_symbols}")

    # Fetch from earliest available date — yfinance will cap at the listing date automatically.
    # This gives us the full history needed for robust EMA-200, RS, and score computation.
    end_date = datetime.today().strftime('%Y-%m-%d')
    start_date = "1990-01-01"  # yfinance will truncate to actual listing date

    inserted_any = False

    for symbol in missing_symbols:
        df = pd.DataFrame()
        symbol_upper = symbol.upper().strip()

        # --- Try NSE first ---
        ticker_ns = f"{symbol_upper}.NS"
        logger.info(f"[INGEST] Trying NSE: {ticker_ns}")
        try:
            raw = yf.download(ticker_ns, start=start_date, end=end_date, progress=False, auto_adjust=True)
            if raw is not None and not raw.empty:
                df = _flatten_yfinance_columns(raw, ticker_ns)
                logger.info(f"[INGEST] {ticker_ns} → {len(df)} rows downloaded.")
        except Exception as e:
            logger.warning(f"[INGEST] {ticker_ns} download failed: {e}")

        # --- Fallback to BSE ---
        if df.empty:
            ticker_bo = f"{symbol_upper}.BO"
            logger.info(f"[INGEST] NSE empty. Trying BSE: {ticker_bo}")
            try:
                raw = yf.download(ticker_bo, start=start_date, end=end_date, progress=False, auto_adjust=True)
                if raw is not None and not raw.empty:
                    df = _flatten_yfinance_columns(raw, ticker_bo)
                    logger.info(f"[INGEST] {ticker_bo} → {len(df)} rows downloaded.")
            except Exception as e:
                logger.warning(f"[INGEST] {ticker_bo} download failed: {e}")

        if df.empty:
            logger.error(f"[INGEST] FAILED: No data found for {symbol_upper} on NSE or BSE.")
            continue

        # --- Validate columns ---
        logger.info(f"[INGEST] Columns available for {symbol_upper}: {list(df.columns)}")

        if "close" not in df.columns:
            # yfinance sometimes returns 'adj_close' only
            if "adj_close" in df.columns:
                df["close"] = df["adj_close"]
            else:
                logger.error(f"[INGEST] No 'close' column for {symbol_upper}. Skipping.")
                continue

        # Fill missing OHLCV columns
        for col in ["open", "high", "low"]:
            if col not in df.columns:
                df[col] = df["close"]
        if "volume" not in df.columns:
            df["volume"] = 0

        # Map adjusted_close
        if "adj_close" in df.columns:
            df["adjusted_close"] = df["adj_close"]
        else:
            df["adjusted_close"] = df["close"]

        # Ensure date column is datetime
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"]).dt.date
        else:
            logger.error(f"[INGEST] No 'date' column for {symbol_upper}. Skipping.")
            continue

        df["symbol"] = symbol_upper
        df = df[["symbol", "date", "open", "high", "low", "close", "adjusted_close", "volume"]]
        df = df.dropna(subset=["close"])

        if df.empty:
            logger.error(f"[INGEST] After cleanup, DataFrame for {symbol_upper} is empty. Skipping.")
            continue

        try:
            records = df.to_dict("records")
            insert_daily_prices(records)
            inserted_any = True
            logger.info(f"[INGEST] ✅ Inserted {len(records)} rows for {symbol_upper} into daily_prices.")
        except Exception as e:
            logger.error(f"[INGEST] DB insert failed for {symbol_upper}: {e}")

    # --- Trigger incremental indicator + score engines ---
    if inserted_any:
        logger.info("[INGEST] Running incremental indicator engine...")
        try:
            add_indicator_columns_if_missing()
            data_df, idx_df = fetch_data_for_symbols(missing_symbols)
            if data_df is not None and not data_df.empty:
                updates = compute_indicators(data_df, idx_df)
                if updates:
                    update_db_with_indicators(updates)
                    logger.info(f"[INGEST] Indicator engine: {len(updates)} row(s) updated.")
        except Exception as e:
            logger.error(f"[INGEST] Indicator engine failed: {e}")

        logger.info("[INGEST] Running incremental stock score engine...")
        try:
            create_market_regime_and_scores_tables()
            compute_stock_scores()
            logger.info("[INGEST] Stock score engine complete.")
        except Exception as e:
            logger.error(f"[INGEST] Stock score engine failed: {e}")
    else:
        logger.warning("[INGEST] No new data inserted. Skipping engine triggers.")

    # --- Re-run the full portfolio analysis with new data ---
    logger.info("[INGEST] Generating final portfolio Risk Audit report...")
    final_report = None
    conn = None
    try:
        conn = get_connection()
        # NOTE: analyze_portfolio signature is (holdings, conn=None)
        final_report = analyze_portfolio(original_holdings, conn=conn)
        logger.info(f"[INGEST] Final report generated: {final_report.get('risk_level')} risk.")
    except Exception as e:
        logger.error(f"[INGEST] Final report generation failed: {e}")
    finally:
        if conn:
            conn.close()

    if final_report:
        logger.info(f"[INGEST] Sending Risk Audit email to {email}...")
        try:
            send_portfolio_review_email(email, name, final_report)
        except Exception as e:
            logger.error(f"[INGEST] Email send failed: {e}")
    else:
        logger.error("[INGEST] No final report to send. Email skipped.")

    logger.info("[INGEST] Async ingestion pipeline finished.")


def send_portfolio_review_email(email: str, name: str, report: dict):
    """Formats and sends the final Risk Audit report via AWS SES."""
    import boto3
    import os

    SENDER_EMAIL = os.getenv("SES_SENDER_EMAIL", "edwardjsi@gmail.com")
    AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
    ses = boto3.client("ses", region_name=AWS_REGION)

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

            <div style="background:#f1f5f9;padding:16px;border-radius:8px;margin-bottom:24px">
                <p style="margin:0 0 8px;font-weight:600;color:#1e293b;font-size:14px">Diagnosis</p>
                <p style="margin:0 0 12px;color:#475569;font-size:14px;line-height:1.5">{report.get('risk_level_description','')}</p>
                <p style="margin:0;color:#475569;font-size:14px;line-height:1.5;font-weight:500">{report.get('summary','')}</p>
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

            <hr style="border:none;border-top:1px solid #e5e7eb;margin:30px 0 20px">
            <p style="font-size:12px;color:#9ca3af;text-align:center">
                This is not financial advice.<br>
                Market Regime Intelligence — Quantitative Signal Platform
            </p>
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
        logger.info(f"[INGEST] ✅ Risk Audit email sent to {email}")
        return True
    except Exception as e:
        logger.error(f"[INGEST] ❌ Email send failed to {email}: {e}")
        return False
