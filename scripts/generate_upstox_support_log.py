import os
import requests
import urllib.parse
from dotenv import load_dotenv

load_dotenv('.env')
token = os.environ.get('UPSTOX_ACCESS_TOKEN', '').strip()
if not token:
    print("Error: UPSTOX_ACCESS_TOKEN not found in .env")
    exit(1)

masked_token = f"{token[:15]}...[REDACTED]...{token[-5:]}" if len(token) > 20 else "[REDACTED]"

print("============================================================")
print(" UPSTOX ANALYTICS TOKEN - API DIAGNOSTIC LOG ")
print("============================================================")
print(f"Token Type: Analytics Token")
print(f"Token Used: Bearer {masked_token}")
print("============================================================\n")

endpoints = [
    {
        "name": "Test 1: Historical Candle V3 (Equity)",
        "url": "https://api.upstox.com/v3/historical-candle/NSE_EQ%7CINE002A01018/days/1/2026-08-15/2026-08-01"
    },
    {
        "name": "Test 2: Instrument Search (V2)",
        "url": "https://api.upstox.com/v2/instrument/search?search_text=RELIANCE"
    }
]

headers = {
    'Authorization': f'Bearer {token}',
    'Accept': 'application/json'
}

for ep in endpoints:
    print(f"> {ep['name']}")
    print(f"> GET {ep['url']}")
    
    try:
        r = requests.get(ep['url'], headers=headers)
        print(f"< HTTP Status: {r.status_code}")
        
        text = r.text
        if token in text:
            text = text.replace(token, "<TOKEN_REDACTED>")
            
        print(f"< Response: {text}\n")
    except Exception as e:
        print(f"< Error: {e}\n")

print("============================================================")
print(" END OF LOG ")
print("============================================================")
