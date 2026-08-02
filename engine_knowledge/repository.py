import os
import sys
import json
from datetime import datetime
from typing import Optional

sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))
from engine_core.db import get_connection
from engine_knowledge.models import (
    CompanyKnowledge, KnowledgeMetadata, Fact, Entity, Observation
)

class KnowledgeRepository:
    """
    Repository to fetch raw compiled JSON artifacts from the database 
    and map them into the strictly typed CompanyKnowledge domain model.
    """
    def get_company_knowledge(self, symbol: str) -> Optional[CompanyKnowledge]:
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                "SELECT company_knowledge, updated_at FROM mosi_compiled_artifacts WHERE symbol = %s",
                (symbol.upper(),)
            )
            row = cur.fetchone()
            if not row:
                return None
                
            raw_knowledge = row["company_knowledge"] or {}
            updated_at = row["updated_at"]
            
            # Calculate age (dummy logic for now, assumes updated_at is datetime)
            age_days = (datetime.now().date() - updated_at.date()).days if updated_at else 0
            
            # Map database JSON to strongly typed domain model
            # Assuming raw_knowledge contains facts, entities, observations
            # Since MOSI schema might differ slightly, we adapt it cleanly here.
            
            raw_facts = raw_knowledge.get("facts", [])
            facts = [
                Fact(
                    fact_id=f.get("fact_id", f"FCT-{i}"),
                    category=f.get("category", "General"),
                    metric=f.get("metric"),
                    value=str(f.get("value", "")),
                    source=f.get("source")
                ) for i, f in enumerate(raw_facts)
            ]
            
            raw_entities = raw_knowledge.get("entities", [])
            entities = [
                Entity(
                    entity_id=e.get("entity_id", f"ENT-{i}"),
                    name=e.get("name", "Unknown"),
                    type=e.get("type", "Unknown")
                ) for i, e in enumerate(raw_entities)
            ]
            
            raw_observations = raw_knowledge.get("observations", [])
            observations = [
                Observation(
                    observation_id=o.get("observation_id", f"OBS-{i}"),
                    type=o.get("type", "UNKNOWN"),
                    entity_id=o.get("entity_id"),
                    value=bool(o.get("value", True)),
                    source_fact=o.get("source_fact"),
                    grounding=o.get("grounding", "VERIFIED")
                ) for i, o in enumerate(raw_observations)
            ]
            
            metadata = KnowledgeMetadata(
                knowledge_version=raw_knowledge.get("version", 1),
                compiler_version=raw_knowledge.get("compiler_version", "1.0"),
                knowledge_age_days=age_days,
                last_refresh=updated_at.isoformat() if updated_at else datetime.now().isoformat(),
                is_stale=age_days > 90
            )
            
            return CompanyKnowledge(
                symbol=symbol.upper(),
                metadata=metadata,
                facts=facts,
                entities=entities,
                observations=observations
            )
            
        finally:
            cur.close()
            conn.close()
