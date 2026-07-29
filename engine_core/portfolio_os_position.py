from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass(frozen=True)
class PortfolioPosition:
    """Immutable state of a portfolio holding at a specific point in time."""

    symbol: str
    entry_price: float
    current_price: float
    quantity: int
    weeks_held: int
    highest_price_since_entry: float
    current_allocation: float  # e.g., 0.05 for 5% of total portfolio
    number_of_tranches: int
    current_stop: float
    current_state: str  # e.g., WATCHLIST, BUY, FIRST TRANCHE, FULL POSITION

    def __post_init__(self):
        if not self.symbol or not self.symbol.strip():
            raise ValueError("symbol is required")
        if self.quantity < 0:
            raise ValueError("quantity cannot be negative")
        if self.current_allocation < 0 or self.current_allocation > 1:
            raise ValueError("current_allocation must be between 0 and 1")
