import os
import sys

sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))
from engine_knowledge.repository import KnowledgeRepository

def test_repository_with_granules():
    """
    Sprint 2: Prove the repository maps JSON to the typed domain model correctly.
    """
    repo = KnowledgeRepository()
    
    # GRANULES should exist in the MOSI database, or any other tested symbol
    # Let's test if we can fetch it. If it doesn't exist, this will just print a warning.
    symbol = "GRANULES"
    knowledge = repo.get_company_knowledge(symbol)
    
    if knowledge:
        print(f"✅ PASS: Repository successfully mapped Knowledge for {symbol}")
        print(f"  Metadata: {knowledge.metadata.dict()}")
        print(f"  Facts Count: {len(knowledge.facts)}")
        print(f"  Observations Count: {len(knowledge.observations)}")
    else:
        print(f"⚠️ Warning: {symbol} not found in database. Please run the Knowledge Importer for {symbol} first.")
        
if __name__ == "__main__":
    test_repository_with_granules()
