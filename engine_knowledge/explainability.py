from __future__ import annotations
from typing import List, Optional, Literal
from pydantic import BaseModel, Field

NodeType = Literal["DECISION", "RULE", "OBSERVATION", "FACT"]

class ExplainNode(BaseModel):
    """
    The universal recursive node for the CAI Explainability Framework.
    Every layer of the platform maps its logic into this single structure.
    """
    type: NodeType
    id: str
    status: Optional[str] = None
    title: Optional[str] = None
    quote: Optional[str] = None
    children: List[ExplainNode] = Field(default_factory=list)

class ExplainTree(BaseModel):
    """
    The root wrapper for a model's explainability tree.
    """
    model: str
    result: str
    children: List[ExplainNode] = Field(default_factory=list)
