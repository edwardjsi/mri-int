import pandas as pd
import numpy as np
from engine_core.rrg_indicators import compute_rrg_indicators

dates = pd.date_range("2026-01-01", periods=30, freq="D")
benchmark_close = pd.Series(100.0, index=dates)

stock_weak = pd.Series(np.linspace(100, 150, 30), index=dates)
stock_weak.iloc[-5:] = [148, 148, 147, 146, 145] # dropping
df_weak = compute_rrg_indicators(stock_weak, benchmark_close, window=5).dropna()
print(df_weak.tail())
