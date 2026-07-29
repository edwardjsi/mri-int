from typing import Optional
import psycopg2.extras

from engine_core.db import get_connection
from engine_core.portfolio_os_position import PortfolioPosition


class PortfolioPositionNotFoundError(Exception):
    pass


class PortfolioPositionRepository:
    def __init__(self):
        pass

    def get_position_by_id(self, position_id: str, conn=None) -> PortfolioPosition:
        """
        Fetches a position by its ID and maps it to the PortfolioPosition data class.
        Includes looking up the current price from daily_prices.
        """
        owns_conn = False
        if conn is None:
            conn = get_connection()
            owns_conn = True

        try:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                # 1. Fetch the base position
                cur.execute(
                    """
                    SELECT symbol, quantity, average_price, allocation, tranche, status
                    FROM cai_position
                    WHERE id = %s
                    """,
                    (position_id,),
                )
                row = cur.fetchone()
                
                if not row:
                    raise PortfolioPositionNotFoundError(f"No position found with id {position_id}")

                symbol = row['symbol']

                # 2. Fetch the current price
                cur.execute(
                    """
                    SELECT close 
                    FROM daily_prices 
                    WHERE symbol = %s 
                    ORDER BY date DESC 
                    LIMIT 1
                    """,
                    (symbol,)
                )
                price_row = cur.fetchone()
                current_price = float(price_row['close']) if price_row else float(row['average_price'])

                # For Phase 1, we default weeks_held, highest_price_since_entry, and current_stop
                # as they require complex ledger queries not yet fully implemented.
                weeks_held = 0
                highest_price_since_entry = current_price  # Placeholder
                current_stop = 0.0  # Placeholder

                return PortfolioPosition(
                    symbol=symbol,
                    entry_price=float(row['average_price']),
                    current_price=current_price,
                    quantity=int(row['quantity']),
                    weeks_held=weeks_held,
                    highest_price_since_entry=highest_price_since_entry,
                    current_allocation=float(row['allocation']) / 100.0 if row['allocation'] else 0.0,
                    number_of_tranches=int(row['tranche']),
                    current_stop=current_stop,
                    current_state=row['status']
                )
        finally:
            if owns_conn and not conn.closed:
                conn.close()
