import yfinance as yf

def check_bank(symbol):
    print(f"\n--- {symbol} ---")
    stock = yf.Ticker(symbol)
    q_income = stock.quarterly_financials
    print("Columns:", q_income.index.tolist())
    # print(q_income.iloc[:, 0]) # Print latest quarter

if __name__ == "__main__":
    check_bank("HDFCBANK.NS")
    check_bank("RELIANCE.NS") # For comparison
