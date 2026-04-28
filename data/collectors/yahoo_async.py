import asyncio
import aiohttp
import yfinance as yf
from diskcache import Cache
from tenacity import retry, stop_after_attempt, wait_exponential
import os

# Ensure cache directory exists
CACHE_DIR = os.path.join(os.getcwd(), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)
cache = Cache(CACHE_DIR)

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
async def fetch_one(ticker):
    if ticker in cache:
        return cache[ticker]

    loop = asyncio.get_event_loop()
    try:
        stock = await loop.run_in_executor(None, yf.Ticker, ticker)
        income = await loop.run_in_executor(None, lambda: stock.financials)
        balance = await loop.run_in_executor(None, lambda: stock.balance_sheet)

        if income is None or income.empty or balance is None or balance.empty:
            return {"error": "no_data", "ticker": ticker}

        income = income.T
        balance = balance.T

        data = []
        for dt in income.index:
            y = dt.year
            row_i = income.loc[dt]
            # Match the date in balance sheet if possible
            if dt in balance.index:
                row_b = balance.loc[dt]
            else:
                # Fallback to the closest year if exact date doesn't match
                row_b = balance.iloc[0] # Very crude fallback

            rec = {
                "year": y,
                "revenue": float(row_i.get("Total Revenue", 0)) if row_i.get("Total Revenue") else 0,
                "ebitda": float(row_i.get("EBITDA", 0)) if row_i.get("EBITDA") else 0,
                "net_profit": float(row_i.get("Net Income", 0)) if row_i.get("Net Income") else 0,
                "total_assets": float(row_b.get("Total Assets", 0)) if row_b.get("Total Assets") else 0,
                "receivables": float(row_b.get("Net Receivables", 0)) if row_b.get("Net Receivables") else 0,
                "inventory": float(row_b.get("Inventory", 0)) if row_b.get("Inventory") else 0,
                "debt": float((row_b.get("Short Long Term Debt", 0) or 0)) + float((row_b.get("Long Term Debt", 0) or 0)),
                "equity": float(row_b.get("Total Stockholder Equity", 0)) if row_b.get("Total Stockholder Equity") else 0
            }
            
            if rec["total_assets"] and rec["receivables"]:
                rec["capital_employed"] = rec["total_assets"] - rec["receivables"]
            else:
                rec["capital_employed"] = None

            data.append(rec)

        data = sorted(data, key=lambda x: x["year"])[-10:]
        payload = {"ticker": ticker, "financials": data}

        cache[ticker] = payload
        return payload
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return {"error": str(e), "ticker": ticker}


async def fetch_batch(tickers, concurrency=8):
    sem = asyncio.Semaphore(concurrency)

    async def bound(t):
        async with sem:
            return await fetch_one(t)

    tasks = [bound(t) for t in tickers]
    return await asyncio.gather(*tasks)
