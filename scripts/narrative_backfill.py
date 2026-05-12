import sys
import os
import datetime
import json
from engine_fundamental.narrative_engine import NarrativeEngine

def backfill():
    # 1. HAL Data
    hal_text = """
    Hindustan Aeronautics Limited (HAL) achieved record revenue of INR 30,381 crores for FY 2023-24, 13% YoY. 
    Manpower costs reduced from 23% to 17% of revenue. Order book at INR 94,000 crores.
    Management projected order book to reach INR 1.2 Lakh Cr by March 2025. 
    Pipeline of INR 1.6-1.7 Lakh Cr expected over next 18-36 months including LCA Mark-1A.
    R&D at 7-8% of revenue. Guidance of 15-18% annual growth for FY25-28.
    """
    
    # 2. VOLTAMP Data
    voltamp_text = """
    Voltamp Transformers Q4 FY24 Net Sales at Rs 504 Cr (+15% YoY). EBITDA Margin 19.83%. 
    Q1 FY25 Net Sales at Rs 428 Cr (+33% YoY). Net Profit Rs 101 Cr (+48% YoY).
    Management highlights strong demand in industrial transformers. Sequential dip in Q1 due to seasonality but YoY growth remains robust.
    """
    
    # 3. KPIGREEN Data
    kpigreen_text = """
    KPI Green Energy FY24 Net Profit at Rs 161 Cr (+47% YoY). Capacity at 445 MW.
    Target of 1000 MW (1 GW) by 2025. Order book 3.5x to 4x of FY24 sales run-rate.
    Management guidance of 45-50% earnings CAGR for FY24-FY26.
    Transitioning to asset-backed renewable energy platform.
    """
    
    # 4. CPPLUS Data (Aditya Infotech)
    cpplus_text = """
    Aditya Infotech (CP PLUS brand) listed via IPO in August 2025. 
    Company was private during FY24 and early FY25, hence no public concalls for those periods.
    Post-listing focus on market share in security surveillance and expansion into smart home segment.
    """

    backfills = [
        ("HAL", hal_text, datetime.date(2024, 5, 17)),
        ("VOLTAMP", voltamp_text, datetime.date(2024, 5, 20)),
        ("KPIGREEN", kpigreen_text, datetime.date(2024, 4, 30)),
        ("CPPLUS", cpplus_text, datetime.date(2025, 8, 20))
    ]
    
    for symbol, text, date in backfills:
        print(f"Analyzing Narrative for {symbol}...")
        engine = NarrativeEngine(symbol)
        # Mocking financial deltas for context
        res = engine.analyze_transcript(text, date, financial_deltas={"growth": "strong", "margin": "improving"})
        if res:
            print(f"SUCCESS: {symbol} Narrative Stored.")
        else:
            print(f"FAILED: {symbol} Narrative Analysis.")

if __name__ == "__main__":
    backfill()
