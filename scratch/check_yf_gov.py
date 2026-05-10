import yfinance as yf
import json

def check_info(symbol):
    print(f"\n--- {symbol} ---")
    stock = yf.Ticker(symbol)
    info = stock.info
    # Print keys that might be related to governance or holders
    gov_keys = ['auditRisk', 'shareHolderRightsRisk', 'governanceEpochDate']
    for k in gov_keys:
        print(f"{k}: {info.get(k)}")
    
    # Also check major_holders
    print("\nMajor Holders:")
    try:
        print(stock.major_holders)
    except:
        print("Failed to fetch major_holders")

if __name__ == "__main__":
    check_info("ADANIENT.NS")
    check_info("TCS.NS")
    check_info("RELIANCE.NS")
