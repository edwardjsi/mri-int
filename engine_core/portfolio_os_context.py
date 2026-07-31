from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from engine_core.portfolio_os_snapshot import StockSnapshot
from engine_core.portfolio_os_position import PortfolioPosition


@dataclass(frozen=True)
class PortfolioContext:
    """Immutable state of the overall portfolio at a point in time."""
    cash: float
    total_value: float
    health_score: float


@dataclass(frozen=True)
class DecisionContext:
    """
    Immutable context object provided to the Rule Engine.
    It combines all necessary facts (stock, position, portfolio) into a single evaluable object.
    """
    stock_snapshot: StockSnapshot
    portfolio_position: Optional[PortfolioPosition] = None
    portfolio_context: Optional[PortfolioContext] = None
    rule_set: Optional[str] = None
    
    # CIW Extension fields (Phase 2 Compatibility)
    ciw_thesis: Optional[str] = None
    ciw_business_quality: Optional[str] = None
    ciw_risks: Optional[list] = None
    ciw_catalysts: Optional[list] = None
    ciw_monitoring: Optional[list] = None

    def __post_init__(self):
        if not self.stock_snapshot:
            raise ValueError("stock_snapshot is required to build a DecisionContext")
