from typing import List, Optional
from pydantic import BaseModel

class Fact(BaseModel):
    fact_id: str
    category: str
    metric: Optional[str] = None
    value: str
    source: Optional[str] = None

class Entity(BaseModel):
    entity_id: str
    name: str
    type: str

class Observation(BaseModel):
    observation_id: str
    type: str
    entity_id: Optional[str] = None
    value: bool
    source_fact: Optional[str] = None
    grounding: str = "VERIFIED"

class KnowledgeMetadata(BaseModel):
    knowledge_version: int
    compiler_version: str
    knowledge_age_days: int
    last_refresh: str
    is_stale: bool

class CompanyKnowledge(BaseModel):
    symbol: str
    metadata: KnowledgeMetadata
    facts: List[Fact]
    entities: List[Entity]
    observations: List[Observation]

class RuleEvidence(BaseModel):
    rule: str
    rule_version: str
    status: str
    observations: List[str]
    quotes: List[str]

class EvidencePayload(BaseModel):
    symbol: str
    evidence: List[RuleEvidence]
