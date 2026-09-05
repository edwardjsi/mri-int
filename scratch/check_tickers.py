import yfinance as yf

symbols = ["ADITYAINFO", "MACFOS", "TITANBIO", "KWALITY"]

for sym in symbols:
    # Try .NS
    df_ns = yf.download(f"{sym}.NS", period="1d", progress=False)
    # Try .BO
    df_bo = yf.download(f"{sym}.BO", period="1d", progress=False)
    print(f"{sym} -> .NS empty: {df_ns.empty}, .BO empty: {df_bo.empty}")
