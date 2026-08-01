import json
import os
import uuid
from typing import Dict, Any, List
from datetime import datetime

class MosiCompiler:
    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return json.load(f)
        return {
            "schema_version": "1.0",
            "supported_documents": ["MOSI"],
            "llm": "mock", # placeholder for now
            "temperature": 0,
            "rules": []
        }
        
    def process_report(self, report_text: str, document_metadata: Dict[str, Any], output_dir: str):
        """
        Processes a MOSI report (mocked extraction for the vertical slice).
        In a real implementation, this would call an LLM with strict JSON schemas.
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # 1. Generate Mock Artifacts based on the spec
        company_facts = self._generate_mock_facts(document_metadata)
        company_knowledge = self._generate_mock_knowledge()
        
        # 2. Write company_facts.json
        facts_path = os.path.join(output_dir, 'company_facts.json')
        with open(facts_path, 'w') as f:
            json.dump(company_facts, f, indent=2)
            
        # 3. Write company_knowledge.json
        knowledge_path = os.path.join(output_dir, 'company_knowledge.json')
        with open(knowledge_path, 'w') as f:
            json.dump(company_knowledge, f, indent=2)
            
        # 4. Write extraction_report.json
        extraction_report = self._generate_extraction_report()
        report_path = os.path.join(output_dir, 'extraction_report.json')
        with open(report_path, 'w') as f:
            json.dump(extraction_report, f, indent=2)
            
        # 5. Write knowledge_manifest.json
        manifest = self._generate_manifest(company_facts, company_knowledge)
        manifest_path = os.path.join(output_dir, 'knowledge_manifest.json')
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
            
        return {
            "status": "success",
            "manifest": manifest
        }
        
    def _generate_mock_facts(self, doc_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [{
            "fact_id": "KNW-FIN-000234",
            "entity_id": "ENT-COMP-001",
            "category": "FINANCIAL",
            "metric_name": "Revenue_CAGR",
            "value": 24.0,
            "unit": "PERCENTAGE",
            "temporal_context": {
                "period_type": "MULTI_YEAR",
                "period_label": "FY21-FY26",
                "effective_date": "2026-03-31",
                "source_date": doc_metadata.get("published_on", "2026-08-01")
            },
            "evidence": {
                "heading": "Financial Performance & Margins",
                "paragraph_index": 17,
                "source": doc_metadata,
                "quote": "Revenue CAGR has been 24% over the last five fiscal years."
            },
            "confidence": {
                "value": 1.0,
                "reason": "Explicit numerical statement"
            },
            "status": "ACTIVE",
            "version": 1
        }]
        
    def _generate_mock_knowledge(self) -> Dict[str, Any]:
        return {
            "entity_id": "ENT-COMP-001",
            "entity_name": "Granules India Ltd",
            "business_model": {
                "narrative_summary": "Granules operates as a vertically integrated pharmaceutical manufacturing company.",
                "structured_entities": {
                    "products": ["Paracetamol", "Ibuprofen", "Metformin"],
                    "plants": ["ENT-PLANT-001", "ENT-PLANT-002", "ENT-PLANT-004"],
                    "customer_segments": ["B2B API Supply", "US Generic Rx"]
                }
            },
            "management": {
                "capital_allocation_philosophy": { "narrative": "Prudent allocation", "facts": [] },
                "key_executives": [
                    {
                        "entity_id": "ENT-EXEC-001",
                        "name": "Krishna Prasad",
                        "role": "MD & Chairman"
                    }
                ]
            }
        }
        
    def _generate_extraction_report(self) -> Dict[str, Any]:
        return {
            "execution_time_ms": 1250,
            "missing_fields": 0,
            "coverage_pct": 100.0,
            "hallucinations_flagged": 0,
            "warnings": []
        }
        
    def _generate_manifest(self, facts: List[Dict[str, Any]], knowledge: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "company_ticker": "GRANULES",
            "company_name": knowledge.get("entity_name", "Unknown"),
            "knowledge_version": 1,
            "last_updated": datetime.utcnow().isoformat() + "Z",
            "stats": {
                "total_facts": len(facts),
                "total_entities": 4, 
                "metrics_tracked": 1,
                "missing_schema_fields": 0,
                "knowledge_coverage_pct": 100.0
            },
            "data_artifacts": {
                "facts_file": "company_facts.json",
                "knowledge_file": "company_knowledge.json",
                "report_file": "extraction_report.json"
            }
        }

if __name__ == "__main__":
    compiler = MosiCompiler()
    doc_metadata = {
        "document_id": "DOC-000145",
        "document_type": "MOSI",
        "version": "1.0",
        "published_on": "2026-08-01"
    }
    result = compiler.process_report("Mock report text...", doc_metadata, "output_artifacts/granules")
    print(f"Compilation finished: {result['status']}")
