from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator

class DecisionState(str, Enum):
    QUIT = "QUIT"
    STRUCTURE = "STRUCTURE"
    ALERT = "ALERT"
    ADD = "ADD"
    HOLD = "HOLD"

class RuleCategory(str, Enum):
    TECHNICAL = "Technical"
    FUNDAMENTAL = "Fundamental"
    CAPITAL_ALLOCATION = "Capital Allocation"
    RISK = "Risk"
    PORTFOLIO = "Portfolio"
    MARKET = "Market"

class ThresholdType(str, Enum):
    PRICE = "PRICE"
    EVENT = "EVENT"

class Threshold(BaseModel):
    threshold_type: ThresholdType
    value: float
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    triggered_rules: List[str]
    valid_from: datetime
    valid_until: datetime

class StateTransition(BaseModel):
    from_state: Optional[DecisionState]
    to_state: DecisionState
    timestamp: datetime
    reasoning_snapshot: Dict[str, Any]

class DecisionEvaluation(BaseModel):
    position_id: str
    symbol: str
    decision_state: DecisionState
    decision_confidence: float = Field(ge=0.0, le=1.0)
    decision_stability: float = Field(ge=0.0, le=1.0)
    decision_expiry: datetime
    rule_satisfaction_score: float = Field(ge=0.0, le=1.0)
    why: str
    why_not_add: Optional[str] = None
    thresholds: List[Threshold]
    triggered_rules: List[str]
    rule_categories: List[RuleCategory]
    portfolio_context: Dict[str, Any]
    last_updated: datetime
    history: List[StateTransition]
    engine_version: str = "2.1.0"
    rule_set_version: str = "1.0.0"
    schema_version: str = "1.0.0"

    @validator("why_not_add", always=True)
    def check_why_not_add(cls, v, values):
        state = values.get("decision_state")
        if state and state != DecisionState.ADD and not v:
            raise ValueError("why_not_add is mandatory whenever state is not ADD")
        return v

class DecisionLedgerEntry(BaseModel):
    position_id: str
    symbol: str
    from_state: Optional[DecisionState]
    to_state: DecisionState
    reasoning_snapshot: Dict[str, Any]
    confidence: float = Field(ge=0.0, le=1.0)
    stability: float = Field(ge=0.0, le=1.0)
    rule_satisfaction_score: float = Field(ge=0.0, le=1.0)
    timestamp: datetime
    expiry: datetime
    triggered_rules: List[str]
    threshold_references: List[Dict[str, Any]]
