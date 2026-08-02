import sys
import os
import json
sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))

from engine_mosi.mosi_compiler import MosiCompiler

compiler = MosiCompiler()
doc_metadata = {"document_id": "TEST", "document_type": "MOSI", "version": "1.0", "published_on": "2026-08-01"}

json_payload = """
{
  "company_facts": [],
  "company_knowledge": {
    "entity_id": "ENT-COMP-KWALITY",
    "entity_name": "Kwality Pharma"
  }
}
"""

try:
    result = compiler.process_report(json_payload, doc_metadata, "../output_artifacts/TEST")
    print(result)
except Exception as e:
    print(f"Error: {e}")
