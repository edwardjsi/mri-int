import pytest
import pandas as pd
import numpy as np

from engine_core.rrg_indicators import compute_rrg_indicators

def test_golden_rrg_dataset():
    """
    Regression test for the MRI RRG Approximation V1.0.
    This locks in the exact JdK standard mathematics. Any optimization or refactoring
    must produce exactly these numbers.
    """
    # Create deterministic mock data
    dates = pd.date_range("2026-01-01", periods=20, freq="D")
    
    # Benchmark rises steadily by 1.0 each day
    benchmark_close = pd.Series(np.linspace(100, 119, 20), index=dates)
    
    # Stock rises faster than benchmark early on, then drops sharply
    stock_values = np.linspace(50, 69, 20)
    stock_values[15:] = [55, 52, 50, 48, 45]  # sharp drop
    stock_close = pd.Series(stock_values, index=dates)
    
    # Calculate with a tiny window of 3 so we get output within our 20-day dataset
    df = compute_rrg_indicators(stock_close, benchmark_close, window=3)
    
    # Drop NaNs due to rolling window
    df = df.dropna()
    
    assert len(df) > 0, "Should have computed RRG values"
    
    # Spot check the last day (2026-01-20)
    last_row = df.iloc[-1]
    
    # Let's mathematically verify the expected values for the last row
    # Last 3 days:
    # Stock: 50, 48, 45
    # Benchmark: 117, 118, 119
    # RS: 50/117=0.427, 48/118=0.406, 45/119=0.378
    # RS_SMA(3) = (0.427 + 0.406 + 0.378) / 3 = 0.403
    # RS_Ratio = 100 * (0.378 / 0.403) = 93.79
    assert round(last_row["jdk_rs_ratio"], 2) == 93.58 
    
    # Prior RS_Ratios for momentum:
    # Day -1 (48, 118): RS=(52/116, 50/117, 48/118) = (0.448, 0.427, 0.406). SMA = 0.427. Ratio = 100*(0.406/0.427) = 95.08
    # Day -2 (50, 117): RS=(55/115, 52/116, 50/117) = (0.478, 0.448, 0.427). SMA = 0.451. Ratio = 100*(0.427/0.451) = 94.67
    # Ratio SMA(3) = (94.67 + 95.08 + 93.68) / 3 = 94.47
    # Momentum = 100 * (93.68 / 94.47) = 99.16
    assert round(last_row["jdk_rs_momentum"], 2) == 99.05
    
    # Quadrant: Ratio < 100 and Momentum < 100 -> LAGGING
    assert last_row["rrg_quadrant"] == "LAGGING"
    
    # Heading: atan2(99.16-100, 93.68-100) = atan2(-0.84, -6.32) -> Quadrant III (approx 187 degrees)
    assert 180 < last_row["rrg_heading"] < 270
    assert round(last_row["rrg_heading"], 2) == 188.42

def test_rrg_quadrants():
    """Test all four RRG quadrants to ensure edge cases map correctly."""
    dates = pd.date_range("2026-01-01", periods=30, freq="D")
    
    # Static benchmark for simplicity
    benchmark_close = pd.Series(100.0, index=dates)
    
    # 1. LEADING (Ratio > 100, Momentum > 100)
    # Stock consistently outperforming and accelerating
    stock_leading = pd.Series(np.linspace(100, 150, 30), index=dates)
    stock_leading.iloc[-5:] = [140, 143, 146, 149, 155] # accelerating upwards
    df_lead = compute_rrg_indicators(stock_leading, benchmark_close, window=5).dropna()
    assert df_lead.iloc[-1]["rrg_quadrant"] == "LEADING"
    
    # 2. WEAKENING (Ratio > 100, Momentum < 100)
    # Stock outperforming but decelerating
    stock_weak = pd.Series(np.linspace(100, 150, 30), index=dates)
    stock_weak.iloc[-5:] = [148, 149, 149.5, 149.8, 149.9] # still > avg but flattening rapidly
    df_weak = compute_rrg_indicators(stock_weak, benchmark_close, window=5).dropna()
    assert df_weak.iloc[-1]["rrg_quadrant"] == "WEAKENING"
    
    # 3. LAGGING (Ratio < 100, Momentum < 100)
    # Stock underperforming and accelerating downwards
    stock_lag = pd.Series(np.linspace(100, 50, 30), index=dates)
    stock_lag.iloc[-5:] = [60, 58, 55, 52, 48] # accelerating downwards
    df_lag = compute_rrg_indicators(stock_lag, benchmark_close, window=5).dropna()
    assert df_lag.iloc[-1]["rrg_quadrant"] == "LAGGING"
    
    # 4. IMPROVING (Ratio < 100, Momentum > 100)
    # Stock underperforming but starting to recover
    stock_improve = pd.Series(np.linspace(100, 50, 30), index=dates)
    stock_improve.iloc[-5:] = [52, 51, 50.5, 50.2, 50.1] # still < avg but flattening rapidly
    df_improve = compute_rrg_indicators(stock_improve, benchmark_close, window=5).dropna()
    assert df_improve.iloc[-1]["rrg_quadrant"] == "IMPROVING"
