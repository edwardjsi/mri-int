import pandas as pd
import numpy as np
from engine_core.db import get_connection
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_5y_quant_backtest():
    """
    Backtests the Deterministic AAE Core (Layers 0, 1, 4, 5) 
    using 5 years of annual fundamental data.
    """
    # 1. Fetch all annual financials
    logger.info("Fetching historical financials...")
    from engine_core.db import fetch_df
    fin_df = fetch_df("SELECT symbol as bse_code, year, revenue, ebitda, net_profit, debt, equity FROM fundamental_financials")
    
    # Build mapping from local BSE CSVs
    logger.info("Building symbol mapping from local CSVs...")
    try:
        bse_a = pd.read_csv("BSET1A.csv", index_col=False)
        bse_b = pd.read_csv("BSET1B.csv", index_col=False)
        bse_master = pd.concat([bse_a, bse_b])
        # Column 'Security Code' is the BSE ID, 'Security Id' is the NSE Ticker
        mapping = dict(zip(bse_master['Security Code'].astype(str), bse_master['Security Id']))
        
        # Ensure bse_code is string for matching
        fin_df['bse_code'] = fin_df['bse_code'].astype(str)
        fin_df['symbol'] = fin_df['bse_code'].map(mapping)
    except Exception as e:
        logger.error(f"Failed to load mapping CSVs: {e}")
        return []
    
    print(f"Total financial rows: {len(fin_df)}")
    fin_df = fin_df.dropna(subset=['symbol'])
    print(f"Financial rows after mapping: {len(fin_df)}")
    
    # 2. Fetch Nifty 50 for benchmark
    logger.info("Fetching benchmark prices...")
    nifty_df = fetch_df("SELECT date, close FROM market_index_prices WHERE symbol = 'NIFTY50' ORDER BY date ASC")
    if nifty_df.empty:
        logger.error("NIFTY50 benchmark data not found in market_index_prices.")
        return []
    nifty_df['date'] = pd.to_datetime(nifty_df['date'])
    
    years = sorted(fin_df['year'].unique())
    print(f"Years available after mapping: {years}")
    results = []

    for year in range(2021, 2026):
        logger.info(f"Processing Year: {year}...")
        
        # Get data for this year and previous year for deltas
        current_fin = fin_df[fin_df['year'] == year].copy()
        prev_fin = fin_df[fin_df['year'] == (year - 1)].copy()
        
        if prev_fin.empty:
            continue
            
        # Merge to get deltas
        merged = pd.merge(current_fin, prev_fin, on="symbol", suffixes=('', '_prev'))
        
        # Calculate Deterministic Score Components
        # Ensure numeric types (convert from Decimal to float)
        for col in ['revenue', 'ebitda', 'debt', 'equity', 'revenue_prev', 'ebitda_prev']:
             merged[col] = merged[col].astype(float).fillna(0)

        # Layer 1: Structural Delta (Growth)
        merged['rev_growth'] = (merged['revenue'] - merged['revenue_prev']) / merged['revenue_prev'].replace(0, np.nan)
        merged['ebitda_growth'] = (merged['ebitda'] - merged['ebitda_prev']) / merged['ebitda_prev'].replace(0, np.nan)
        
        # Layer 0: Risk/Governance (Debt/Equity)
        merged['de_ratio'] = merged['debt'] / merged['equity'].replace(0, np.nan)
        
        # Scoring Logic (Deterministic Core)
        merged['score'] = 0
        merged.loc[merged['rev_growth'] > 0.10, 'score'] += 30 # Relaxed: 10%+ Rev Growth
        merged.loc[merged['ebitda_growth'] > 0.10, 'score'] += 30 # Relaxed: 10%+ EBITDA Growth
        merged.loc[merged['de_ratio'] < 0.8, 'score'] += 20 # Relaxed: Debt/Equity < 0.8
        merged.loc[merged['de_ratio'] > 2.0, 'score'] -= 50 # High Debt Penalty
        
        print(f"Merged rows for {year}: {len(merged)}")
        if not merged.empty:
            print(f"Score distribution for {year}:\n{merged['score'].value_counts().to_dict()}")
        
        # Filter for top candidates
        top_candidates = merged[merged['score'] >= 40].sort_values(by='score', ascending=False).head(10) # Lowered threshold to 40
        
        if top_candidates.empty:
            print(f"No top candidates found for {year}")
            continue
            
        print(f"Top 10 candidates for {year}: {list(top_candidates['symbol'])}")
            
        # Performance Tracking & Hardened Filters
        # We assume entry on first trading day of Year+1
        start_date = f"{year+1}-01-01"
        end_date = f"{year+1}-12-31"
        lookback_start = f"{year}-06-01" # 6 months before entry for RS calculation
        
        # Benchmark Return for RS
        nifty_lookback = nifty_df[(nifty_df['date'] >= pd.to_datetime(lookback_start)) & (nifty_df['date'] <= pd.to_datetime(start_date))]
        if not nifty_lookback.empty:
            nifty_rs_base = (nifty_lookback.iloc[-1]['close'] - nifty_lookback.iloc[0]['close']) / nifty_lookback.iloc[0]['close']
        else:
            nifty_rs_base = 0

        # Filter candidates by Market Confirmation (Momentum)
        logger.info(f"Applying Market Confirmation filters for {year+1}...")
        hardened_candidates = []
        for _, row in merged.iterrows():
            bse_code = row['bse_code']
            price_query = f"""
                SELECT date, close 
                FROM daily_prices 
                WHERE symbol = '{bse_code}' 
                AND date >= '{lookback_start}' AND date <= '{start_date}'
                ORDER BY date ASC
            """
            hist_prices = fetch_df(price_query)
            if hist_prices.empty or len(hist_prices) < 100:
                continue
            
            # 1. EMA 200 Filter (Trend)
            hist_prices['ema200'] = hist_prices['close'].ewm(span=200, adjust=False).mean()
            current_price = hist_prices.iloc[-1]['close']
            ema200 = hist_prices.iloc[-1]['ema200']
            
            if current_price < ema200:
                continue # Reject stocks in downtrend
                
            # 2. Relative Strength (RS) Filter
            stock_rs = (current_price - hist_prices.iloc[0]['close']) / hist_prices.iloc[0]['close']
            if stock_rs < nifty_rs_base:
                continue # Reject underperformers
            
            # Add to hardened pool
            candidate_data = row.to_dict()
            candidate_data['stock_rs'] = stock_rs
            hardened_candidates.append(candidate_data)
            
        if not hardened_candidates:
            print(f"No candidates passed the Market Confirmation filter for {year+1}")
            continue
            
        hardened_df = pd.DataFrame(hardened_candidates)
        top_candidates = hardened_df.sort_values(by=['score', 'stock_rs'], ascending=False).head(10)
        
        print(f"Top 10 Hardened candidates for {year+1}: {list(top_candidates['symbol'])}")
            
        # Get Stock returns for these candidates
        basket_returns = []
        for bse_code in top_candidates['bse_code']:
            price_query = f"""
                SELECT date, close 
                FROM daily_prices 
                WHERE symbol = '{bse_code}' 
                AND date >= '{start_date}' AND date <= '{end_date}'
                ORDER BY date ASC
            """
            prices = fetch_df(price_query)
            if not prices.empty:
                entry_price = float(prices.iloc[0]['close'])
                max_price = entry_price
                exit_price = float(prices.iloc[-1]['close'])
                
                # Simulate daily path for Trailing Stop Loss (15%)
                for _, p_row in prices.iterrows():
                    curr_p = float(p_row['close'])
                    if curr_p > max_price:
                        max_price = curr_p
                    
                    if curr_p < (max_price * 0.85):
                        # STOP LOSS TRIGGERED
                        exit_price = curr_p
                        break
                
                basket_returns.append((exit_price - entry_price) / entry_price)
        
        if not basket_returns:
            continue
            
        avg_basket_return = sum(basket_returns) / len(basket_returns)
        
        # Benchmark Return
        nifty_year = nifty_df[(nifty_df['date'] >= pd.to_datetime(start_date)) & (nifty_df['date'] <= pd.to_datetime(end_date))]
        if not nifty_year.empty:
            n_entry = float(nifty_year.iloc[0]['close'])
            n_exit = float(nifty_year.iloc[-1]['close'])
            nifty_return = (n_exit - n_entry) / n_entry
        else:
            nifty_return = 0.0
            
        results.append({
            "year": year + 1,
            "basket_return": round(float(avg_basket_return) * 100, 2),
            "nifty_return": round(float(nifty_return) * 100, 2),
            "outperformance": round((float(avg_basket_return) - float(nifty_return)) * 100, 2),
            "symbols": list(top_candidates['symbol'])
        })
        
    return results

if __name__ == "__main__":
    backtest_results = run_5y_quant_backtest()
    
    print("\n" + "="*50)
    print("   AAE V3 DETERMINISTIC (80% QUANT) BACKTEST   ")
    print("="*50)
    print(f"{'Year':<6} | {'AAE Basket':<12} | {'Nifty 500':<12} | {'Alpha'}")
    print("-" * 50)
    
    total_alpha = 0
    for r in backtest_results:
        print(f"{r['year']:<6} | {r['basket_return']:>10}% | {r['nifty_return']:>10}% | {r['outperformance']:>8}%")
        total_alpha += r['outperformance']
        
    print("-" * 50)
    if backtest_results:
        print(f"Average Annual Alpha: {round(total_alpha / len(backtest_results), 2)}%")
    print("="*50)
