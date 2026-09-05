import pandas as pd
import yfinance as yf

for sym in ['RELIANCE.NS']:
    data = yf.download(sym, start="2023-01-01", progress=False)
    data = data.reset_index()
    data.columns = [c[0].lower() if isinstance(c, tuple) else c.lower() for c in data.columns]
    print(data.columns)
