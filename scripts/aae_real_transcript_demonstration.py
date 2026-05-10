import os
import sys
import subprocess
import requests
import datetime
import logging

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engine_fundamental.transcript_collector import TranscriptCollector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def ingest_real_transcript(symbol, date, url):
    """
    Download PDF, convert to text, and ingest.
    """
    temp_pdf = f"scratch/{symbol}_transcript.pdf"
    temp_txt = f"scratch/{symbol}_transcript.txt"
    os.makedirs("scratch", exist_ok=True)

    logger.info(f"Downloading transcript for {symbol} from {url}...")
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers, timeout=30)
    with open(temp_pdf, 'wb') as f:
        f.write(response.content)

    logger.info(f"Converting PDF to text...")
    try:
        subprocess.run(['pdftotext', temp_pdf, temp_txt], check=True)
        with open(temp_txt, 'r') as f:
            text = f.read()
    except Exception as e:
        logger.error(f"Failed to convert PDF: {e}")
        return

    logger.info(f"Ingesting text into AAE V3 Narrative Engine...")
    collector = TranscriptCollector()
    collector.store_transcript(symbol, date, text, source_url=url)
    
    logger.info(f"Real Transcript Ingestion Complete for {symbol}")

if __name__ == "__main__":
    # 360ONE April 2026 Transcript
    url = "https://www.bseindia.com/xml-data/corpfiling/AttachHis/694ed4c9-9336-482a-b9c7-fd594b73be1c.pdf"
    ingest_real_transcript("360ONE", "2026-04-27", url)
