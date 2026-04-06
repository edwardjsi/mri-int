"""
MRI Daily Pipeline — [ENGINE_CORE PRODUCTION READY]
"""
import os
import sys
import logging
from datetime import datetime

# TRACING: Final Conductor
print(f"DEBUG: LOADING scripts/mri_pipeline.py from {os.path.abspath(__file__)}")

# Add parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# IMPORT FROM THE RENAMED PACKAGE
from engine_core.db import initialize_core_schema_v100
from engine_core.ingestion_engine import load_indices

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("pipeline")

def run_pipeline():
    logger.info(f"=== MRI Daily Pipeline — {datetime.now().strftime('%Y-%m-%d %H:%M UTC')} — NEW ENGINE_CORE ===")
    
    # 1. BOOTSTRAP
    try:
        initialize_core_schema_v100()
    except Exception as e:
        logger.error(f"SCHEMA FAILED: {e}")

    # 2. INGEST
    logger.info("[1/5] Ingesting Index Data...")
    try:
        load_indices()
    except Exception as e:
        logger.error(f"INGESTION FAILED: {e}")

    logger.info("=== Pipeline Complete (Version 100.1) ===")

if __name__ == "__main__":
    run_pipeline()
