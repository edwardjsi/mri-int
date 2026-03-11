import logging
import asyncio
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from src.db import get_connection, insert_daily_prices
from src.indicator_engine import fetch_data, compute_indicators, update_db_with_indicators, add_indicator_columns_if_missing
from src.regime_engine import compute_stock_scores
from src.email_service import get_connection as get_email_conn
from src.portfolio_review_engine import analyze_portfolio

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def ingest_missing_symbols_async(missing_symbols: list[str], original_holdings: list[dict], client_id: str, email: str, name: str):
    """
    Background task to download historical data for missing symbols via yfinance,
    compute their indicators and scores, and email the completed Risk Audit report.
    """
    logger.info(f"Starting background ingestion for {len(missing_symbols)} missing symbols: {missing_symbols}")
    
    end_date = datetime.today().strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=365)).strftime('%Y-%m-%d')
    
    inserted_any = False
    
    for symbol in missing_symbols:
        df = pd.DataFrame()
        # Try NSE (.NS) first
        ticker_ns = f"{symbol}.NS"
        logger.info(f"Attempting to fetch {ticker_ns}...")
        try:
            df = yf.download(ticker_ns, start=start_date, end=end_date, progress=False, auto_adjust=True)
        except Exception as e:
            logger.warning(f"Failed fetching {ticker_ns}: {e}")
            
        # If NSE fails or is empty, fallback to BSE (.BO)
        if df.empty:
            ticker_bo = f"{symbol}.BO"
            logger.info(f"{symbol}.NS not found or empty. Attempting {ticker_bo}...")
            try:
                df = yf.download(ticker_bo, start=start_date, end=end_date, progress=False, auto_adjust=True)
            except Exception as e:
                logger.warning(f"Failed fetching {ticker_bo}: {e}")
                
        if df.empty:
            logger.error(f"Could not find historical data for {symbol} on NSE or BSE.")
            continue
            
        # Standardize the yfinance dataframe
        df = df.reset_index()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]
            
        df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]
        df["symbol"] = symbol
        
        if "adj_close" in df.columns and "close" not in df.columns:
             df["close"] = df["adj_close"]
             
        if "close" not in df.columns:
             logger.warning(f"No 'close' column found for {symbol}.")
             continue

        for col in ["open", "high", "low", "volume"]:
            if col not in df.columns:
                df[col] = 0.0 if col != "volume" else 0
                
        if "adj_close" in df.columns:
            df["adjusted_close"] = df["adj_close"]
        else:
            df["adjusted_close"] = df["close"]
                
        df = df.rename(columns={"date": "date"})
        df = df[["symbol", "date", "open", "high", "low", "close", "adjusted_close", "volume"]]
        df = df.dropna(subset=["close"])
        
        if not df.empty:
            records = df.to_dict("records")
            insert_daily_prices(records)
            inserted_any = True
            logger.info(f"✅ Successfully ingested {len(records)} days of history for {symbol}")

    if inserted_any:
        logger.info("Triggering incremental indicator engine for new data...")
        add_indicator_columns_if_missing()
        data_df, idx_df = fetch_data()
        if data_df is not None and not data_df.empty:
            updates = compute_indicators(data_df, idx_df)
            if updates:
                update_db_with_indicators(updates)
                
        logger.info("Triggering incremental regime engine (stock scoring)...")
        compute_stock_scores()
        logger.info("Background data ingestion complete!")
    else:
        logger.warning("No new data was inserted. Bypassing engine triggers.")

    # Re-run the portfolio analysis now that the DB has the new symbols
    logger.info("Generating fully updated Risk Audit report...")
    
    # We need a raw connection for analyze_portfolio
    from src.db import get_connection as get_raw_conn
    conn = get_raw_conn()
    try:
        final_report = analyze_portfolio(original_holdings, client_id, conn)
    finally:
        conn.close()
        
    # Email the final report via SES
    logger.info(f"Sending final Risk Audit report email to {email}")
    send_portfolio_review_email(email, name, final_report)
    logger.info("Async processing pipeline finished successfully.")


def send_portfolio_review_email(email: str, name: str, report: dict):
    """Formats and sends the final Risk Audit report via AWS SES."""
    import boto3
    import os
    
    # Reusing SES env vars
    SENDER_EMAIL = os.getenv("SES_SENDER_EMAIL", "edwardjsi@gmail.com")
    AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
    ses = boto3.client("ses", region_name=AWS_REGION)
    
    subject = f"Your Portfolio Risk Audit is Ready: {report['risk_level']} Risk"
    
    regime_color = {"BULL": "#22c55e", "BEAR": "#ef4444", "NEUTRAL": "#f59e0b"}.get(report['regime'], "#6b7280")
    risk_color = {"LOW": "#22c55e", "MODERATE": "#eab308", "HIGH": "#ef4444", "EXTREME": "#ef4444"}.get(report['risk_level'], "#6b7280")
    
    holding_rows = ""
    for h in report['holdings']:
        score_str = f"{h['score']}/5" if h['score'] is not None else "N/A"
        ema_str = "⚠️ YES" if h['below_200ema'] else "NO"
        holding_rows += f"""
        <tr>
            <td style="padding:8px;border-bottom:1px solid #e5e7eb;font-weight:600">{h['symbol']}</td>
            <td style="padding:8px;border-bottom:1px solid #e5e7eb">{score_str}</td>
            <td style="padding:8px;border-bottom:1px solid #e5e7eb">{h['alignment']}</td>
            <td style="padding:8px;border-bottom:1px solid #e5e7eb">{h['weight_pct']}%</td>
            <td style="padding:8px;border-bottom:1px solid #e5e7eb;color:{'#ef4444' if h['below_200ema'] else '#6b7280'}">{ema_str}</td>
        </tr>"""

    html_body = f"""
    <html>
    <body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:600px;margin:0 auto;padding:20px;background:#f9fafb">
        <div style="background:white;border-radius:12px;padding:24px;box-shadow:0 1px 3px rgba(0,0,0,0.1)">
            <h1 style="margin:0 0 16px;font-size:20px;color:#111827">🛡️ Your Requested Risk Audit</h1>
            <p style="color:#374151">Hi {name},</p>
            <p style="color:#374151;margin-bottom:24px">Your portfolio contains {len(report['holdings'])} holdings. Here is the final MRI diagnosis based on today's market regime.</p>
            
            <div style="display:flex;gap:12px;margin-bottom:20px">
                <div style="flex:1;background:{risk_color}15;border-left:4px solid {risk_color};padding:12px;border-radius:4px">
                    <span style="font-size:13px;color:#6b7280">Overall Risk</span>
                    <div style="font-size:18px;font-weight:700;color:{risk_color}">{report['risk_level']}</div>
                    <div style="font-size:12px;color:#6b7280">Score: {report['risk_score_pct']}%</div>
                </div>
                <div style="flex:1;background:{regime_color}15;border-left:4px solid {regime_color};padding:12px;border-radius:4px">
                    <span style="font-size:13px;color:#6b7280">Market Regime</span>
                    <div style="font-size:18px;font-weight:700;color:{regime_color}">{report['regime']}</div>
                </div>
            </div>

            <div style="background:#f1f5f9;padding:16px;border-radius:8px;margin-bottom:24px">
                <p style="margin:0 0 8px;font-weight:600;color:#1e293b;font-size:14px">Diagnosis</p>
                <p style="margin:0 0 12px;color:#475569;font-size:14px;line-height:1.5">{report['risk_level_description']}</p>
                <p style="margin:0;color:#475569;font-size:14px;line-height:1.5;font-weight:500">{report['summary']}</p>
            </div>

            <h2 style="color:#1e293b;font-size:16px;margin:20px 0 8px">Holding Breakdown</h2>
            <table style="width:100%;border-collapse:collapse;font-size:13px">
                <tr style="background:#f8fafc">
                    <th style="padding:8px;text-align:left;color:#475569">Symbol</th>
                    <th style="padding:8px;text-align:left;color:#475569">Score</th>
                    <th style="padding:8px;text-align:left;color:#475569">Alignment</th>
                    <th style="padding:8px;text-align:left;color:#475569">Weight</th>
                    <th style="padding:8px;text-align:left;color:#475569">< 200 EMA</th>
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
        logger.info(f"✅ Risk Audit email sent to {email}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to send final report email to {email}: {e}")
        return False
