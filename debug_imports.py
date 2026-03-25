import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

try:
    from src.ingestion_engine import load_indices
    print("SUCCESS: load_indices imported successfully from src.ingestion_engine")
    print(f"Function object: {load_indices}")
except ImportError as e:
    print(f"IMPORT ERROR: {e}")
    import traceback
    traceback.print_exc()

# Inspect the module
try:
    import src.ingestion_engine
    print(f"Module file: {src.ingestion_engine.__file__}")
    print(f"Module members: {[m for m in dir(src.ingestion_engine) if not m.startswith('__')]}")
except Exception as e:
    print(f"MODULE INSPECTION FAILED: {e}")
