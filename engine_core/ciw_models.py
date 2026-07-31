from enum import Enum
from typing import List, Dict, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field

# --- Foundational Enums ---

class NodeType(str, Enum):
    THESIS = "THESIS"
    BUSINESS_QUALITY = "BUSINESS_QUALITY"
    COMPETITIVE_ADVANTAGE = "COMPETITIVE_ADVANTAGE"
    RISK = "RISK"
    CATALYST = "CATALYST"
    MONITORING = "MONITORING"

class Confidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class Status(str, Enum):
    CREATED = "CREATED"
    ACTIVE = "ACTIVE"
    CONFIRMED = "CONFIRMED"
    RESOLVED = "RESOLVED"
    ARCHIVED = "ARCHIVED"

class EventType(str, Enum):
    RESEARCH = "RESEARCH"
    TRADE = "TRADE"
    EARNINGS = "EARNINGS"
    DECISION = "DECISION"


# --- Core Entities ---

class SourceDocument(BaseModel):
    id: str
    doc_type: str
    title: str
    author: str
    uri: str
    created_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)

class KnowledgeNode(BaseModel):
    id: str
    node_type: NodeType
    text: str
    confidence: Confidence
    status: Status
    evidence: List[Dict[str, Any]] = Field(default_factory=list)  # Must reference SourceDocument.id
    history: List[Dict[str, Any]] = Field(default_factory=list)   # Superseded versions
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)

class TimelineEvent(BaseModel):
    id: str
    event_date: datetime
    event_type: EventType
    summary: str
    reference_id: Optional[str] = None


# --- Aggregate Root Components ---

class CompanyIdentity(BaseModel):
    company_id: str
    symbol: str
    name: str
    sector: Optional[str] = None

class PortfolioContext(BaseModel):
    status: str
    allocation: float
    average_cost: float

class KnowledgeState(BaseModel):
    last_updated: Optional[datetime] = None
    understanding: Dict[str, KnowledgeNode] = Field(default_factory=dict)
    risks: List[KnowledgeNode] = Field(default_factory=list)
    catalysts: List[KnowledgeNode] = Field(default_factory=list)
    monitoring: List[KnowledgeNode] = Field(default_factory=list)


# --- The Aggregate Root ---

class CompanyWorkspace(BaseModel):
    identity: CompanyIdentity
    state: KnowledgeState
    timeline: List[TimelineEvent] = Field(default_factory=list)
    portfolio: PortfolioContext
    last_reviewed: Optional[datetime] = None
    current_decision: Optional[str] = None
    current_trend: Optional[str] = None

# --- Update Transaction Models ---

class NodeUpdate(BaseModel):
    node_type: NodeType
    text: str
    confidence: Confidence = Confidence.MEDIUM
    status: Status = Status.ACTIVE
    operation: str  # "CREATE", "UPDATE", "ARCHIVE"

class KnowledgeUpdateTransaction(BaseModel):
    company_symbol: str
    source_document_id: str
    timeline_summary: str
    node_updates: List[NodeUpdate]

