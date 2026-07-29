import os
import sys
from dataclasses import FrozenInstanceError

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engine_core.portfolio_os_position import PortfolioPosition  # noqa: E402


class TestPortfolioPosition:
    def test_creates_valid_position(self):
        pos = PortfolioPosition(
            symbol="RELIANCE",
            entry_price=2500.0,
            current_price=2600.0,
            quantity=100,
            weeks_held=4,
            highest_price_since_entry=2650.0,
            current_allocation=0.10,
            number_of_tranches=2,
            current_stop=2450.0,
            current_state="FULL POSITION",
        )
        assert pos.symbol == "RELIANCE"
        assert pos.entry_price == 2500.0
        assert pos.current_price == 2600.0
        assert pos.quantity == 100
        assert pos.weeks_held == 4
        assert pos.highest_price_since_entry == 2650.0
        assert pos.current_allocation == 0.10
        assert pos.number_of_tranches == 2
        assert pos.current_stop == 2450.0
        assert pos.current_state == "FULL POSITION"

    def test_requires_symbol(self):
        with pytest.raises(ValueError, match="symbol is required"):
            PortfolioPosition(
                symbol="",
                entry_price=100.0,
                current_price=100.0,
                quantity=10,
                weeks_held=0,
                highest_price_since_entry=100.0,
                current_allocation=0.01,
                number_of_tranches=1,
                current_stop=90.0,
                current_state="FIRST TRANCHE",
            )

    def test_rejects_negative_quantity(self):
        with pytest.raises(ValueError, match="quantity cannot be negative"):
            PortfolioPosition(
                symbol="TCS",
                entry_price=100.0,
                current_price=100.0,
                quantity=-5,
                weeks_held=0,
                highest_price_since_entry=100.0,
                current_allocation=0.01,
                number_of_tranches=1,
                current_stop=90.0,
                current_state="FIRST TRANCHE",
            )

    def test_rejects_invalid_allocation(self):
        with pytest.raises(ValueError, match="current_allocation must be between 0 and 1"):
            PortfolioPosition(
                symbol="TCS",
                entry_price=100.0,
                current_price=100.0,
                quantity=10,
                weeks_held=0,
                highest_price_since_entry=100.0,
                current_allocation=1.5,
                number_of_tranches=1,
                current_stop=90.0,
                current_state="FIRST TRANCHE",
            )

    def test_is_immutable(self):
        pos = PortfolioPosition(
            symbol="HDFC",
            entry_price=1500.0,
            current_price=1550.0,
            quantity=50,
            weeks_held=2,
            highest_price_since_entry=1600.0,
            current_allocation=0.05,
            number_of_tranches=1,
            current_stop=1450.0,
            current_state="FIRST TRANCHE",
        )
        with pytest.raises(FrozenInstanceError):
            pos.current_price = 1600.0
