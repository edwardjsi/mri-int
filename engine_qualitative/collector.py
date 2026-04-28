import requests
from bs4 import BeautifulSoup
from datetime import datetime

def fetch_url_text(url):
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, "html.parser")

        # remove scripts/styles
        for s in soup(["script", "style"]):
            s.extract()

        text = " ".join(soup.stripped_strings)
        return text[:200_000]  # cap size
    except Exception:
        return None

def build_qil_input(ticker, sources):
    """
    sources = [
      {"url": "...", "type": "concall", "date": "2025-01"},
      {"url": "...", "type": "annual_report", "date": "2024-06"}
    ]
    """
    docs = []
    for s in sources:
        txt = fetch_url_text(s["url"])
        if not txt:
            continue
        docs.append({
            "ticker": ticker,
            "source_type": s["type"],
            "date": s["date"],
            "text": txt
        })
    return docs
