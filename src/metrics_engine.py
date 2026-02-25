import pandas as pd
import numpy as np
import logging
import os
from src.db import get_connection

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

INITIAL_CAPITAL = 100000.0
RISK_FREE_RATE = 0.05 # 5% assumed risk free rate for Sharpe/Sortino
TRADING_DAYS_PER_YEAR = 252

def calculate_drawdown(equity_series):
    rolling_max = equity_series.expanding(min_periods=1).max()
    drawdown = (equity_series / rolling_max) - 1.0
    return drawdown

def calculate_metrics(dates, prices_or_equity, name="Strategy"):
    """Calculate core quantitative metrics for a given equity or price series"""
    series = pd.Series(prices_or_equity, index=pd.to_datetime(dates))
    
    # Daily returns
    returns = series.pct_change().dropna()
    
    # Timeline
    years = (series.index[-1] - series.index[0]).days / 365.25
    
    # Cumulative return
    total_return = (series.iloc[-1] / series.iloc[0]) - 1.0
    
    # CAGR
    cagr = ((series.iloc[-1] / series.iloc[0]) ** (1 / years)) - 1.0
    
    # Max Drawdown
    drawdown = calculate_drawdown(series)
    max_dd = drawdown.min()
    
    # Volatility (Annualized)
    annual_volatility = returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR)
    
    # Sharpe Ratio
    excess_returns = returns - (RISK_FREE_RATE / TRADING_DAYS_PER_YEAR)
    sharpe = (excess_returns.mean() / returns.std()) * np.sqrt(TRADING_DAYS_PER_YEAR) if returns.std() != 0 else 0
    
    # Sortino Ratio (Downside deviation only)
    negative_returns = returns[returns < 0]
    downside_std = negative_returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR)
    sortino = (excess_returns.mean() * TRADING_DAYS_PER_YEAR) / downside_std if downside_std != 0 else 0
    
    # Calmar Ratio
    calmar = cagr / abs(max_dd) if max_dd != 0 else 0
    
    return {
        'Portfolio': name,
        'Total Return (%)': round(total_return * 100, 2),
        'CAGR (%)': round(cagr * 100, 2),
        'Max Drawdown (%)': round(max_dd * 100, 2),
        'Ann. Volatility (%)': round(annual_volatility * 100, 2),
        'Sharpe Ratio': round(sharpe, 2),
        'Sortino Ratio': round(sortino, 2),
        'Calmar Ratio': round(calmar, 2),
        'Years': round(years, 1)
    }

def run_metrics_engine(input_prefix=""):
    logger.info("Initializing Metrics Engine...")
    
    # 1. Load Strategy Data
    try:
        equity_df = pd.read_csv(f'outputs/{input_prefix}equity_curve.csv')
    except FileNotFoundError:
        logger.error(f"outputs/{input_prefix}equity_curve.csv not found! Run portfolio_engine.py first.")
        return
        
    strategy_dates = equity_df['date'].values
    strategy_equity = equity_df['equity'].values
    
    # 2. Load Benchmark Data (NIFTY50)
    logger.info("Fetching NIFTY50 benchmark from DB...")
    conn = get_connection()
    
    start_date = strategy_dates[0]
    end_date = strategy_dates[-1]
    
    # Get benchmark prices aligned to our strategy's dates
    sql = """
        SELECT date, close 
        FROM index_prices 
        WHERE symbol = 'NIFTY50' 
        AND date >= %s AND date <= %s
        ORDER BY date
    """
    bench_df = pd.read_sql(sql, conn, params=(start_date, end_date))
    conn.close()
    
    # Align dates (just in case there are missing index days, we merge)
    bench_df['date'] = bench_df['date'].astype(str)
    equity_df['date'] = equity_df['date'].astype(str)
    
    merged = pd.merge(equity_df, bench_df, on='date', how='inner')
    
    aligned_dates = merged['date'].values
    aligned_strategy = merged['equity'].values
    aligned_benchmark = merged['close'].values
    
    logger.info(f"Computing metrics over {len(aligned_dates)} aligned trading days...")
    
    # 3. Compute
    strat_metrics = calculate_metrics(aligned_dates, aligned_strategy, "MRI MRI-0x Strategy")
    bench_metrics = calculate_metrics(aligned_dates, aligned_benchmark, "NIFTY 50 (Buy & Hold)")
    
    # 4. Consolidate and Export
    results_df = pd.DataFrame([strat_metrics, bench_metrics])
    
    # Reorder columns slightly for printing
    cols = ['Portfolio', 'CAGR (%)', 'Max Drawdown (%)', 'Sharpe Ratio', 'Sortino Ratio', 'Calmar Ratio', 'Total Return (%)', 'Ann. Volatility (%)', 'Years']
    results_df = results_df[cols]
    
    logger.info("\n" + "="*80)
    logger.info("PERFORMANCE REPORT")
    logger.info("="*80)
    logger.info("\n" + results_df.to_string(index=False))
    logger.info("="*80 + "\n")
    
    os.makedirs('outputs', exist_ok=True)
    results_df.to_csv(f'outputs/{input_prefix}performance_summary.csv', index=False)
    results_df.to_markdown(f'outputs/{input_prefix}performance_summary.md', index=False)
    
    logger.info(f"Metrics exported to outputs/{input_prefix}performance_summary.csv and .md")
    
    # Print the Go/No-Go Decision Verdicts
    logger.info("--- GO/NO-GO CRITERIA CHECK ---")
    cagr_pass = strat_metrics['CAGR (%)'] > bench_metrics['CAGR (%)']
    dd_pass = abs(strat_metrics['Max Drawdown (%)']) < abs(bench_metrics['Max Drawdown (%)'])
    sharpe_pass = strat_metrics['Sharpe Ratio'] >= 1.0
    
    logger.info(f"1. CAGR > Nifty: {'✅ PASS' if cagr_pass else '❌ FAIL'}")
    logger.info(f"2. Max Drawdown < Nifty: {'✅ PASS' if dd_pass else '❌ FAIL'}")
    logger.info(f"3. Sharpe Ratio >= 1.0: {'✅ PASS' if sharpe_pass else '❌ FAIL'}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run Metrics Engine")
    parser.add_argument('--input-prefix', type=str, default="", help='Prefix for input CSV files')
    args = parser.parse_args()
    
    run_metrics_engine(input_prefix=args.input_prefix)
