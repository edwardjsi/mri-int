import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

try:
    from src.data_loader import load_indices
    print("SUCCESS: load_indices imported successfully from src.data_loader")
    print(f"Function object: {load_indices}")
except ImportError as e:
    print(f"IMPORT ERROR: {e}")
    import traceback
    traceback.print_exc()

# Inspect the module
try:
    import src.data_loader
    print(f"Module file: {src.data_loader.__file__}")
    print(f"Module members: {[m for m in dir(src.data_loader) if not m.startswith('__')]}")
except Exception as e:
    print(f"MODULE INSPECTION FAILED: {e}")
