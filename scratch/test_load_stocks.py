import sys
from engine_core.ingestion_engine import load_stocks

symbols = ["ADITYAINFO", "MACFOS", "TITANBIO", "STRINGMETAVERSE", "BCSSL"]
load_stocks(symbols)
