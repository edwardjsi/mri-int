import datetime
from typing import Optional

from engine_core.db import get_connection
from engine_core.investment_model import InvestmentModel
from engine_core.model_results_repository import ModelResult

class RrgModel(InvestmentModel):
    """
    RRG (Relative Rotation Graph) Model.
    Acts as a thin consumer of primitives already calculated by the Indicator Engine.
    """
    
    @property
    def id(self) -> str:
        return "RRG"
        
    @property
    def version(self) -> str:
        return "1.0"
        
    def evaluate(self, symbol: str, evaluation_date: Optional[datetime.date] = None) -> ModelResult:
        eval_date = evaluation_date or datetime.date.today()
        
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                # We fetch the closest available row on or before the evaluation_date
                cur.execute(
                    """
                    SELECT date, rrg_quadrant, rrg_heading, jdk_rs_ratio, jdk_rs_momentum, rrg_benchmark
                    FROM daily_prices
                    WHERE symbol = %s AND date <= %s
                    ORDER BY date DESC
                    LIMIT 1
                    """,
                    (symbol, eval_date)
                )
                row = cur.fetchone()
                
                if not row or row["rrg_quadrant"] is None:
                    # Primitives are missing for this symbol
                    return ModelResult(
                        symbol=symbol,
                        model_id=self.id,
                        model_version=self.version,
                        evaluation_date=eval_date,
                        status="FAILED",
                        score=None,
                        payload=None,
                        error_message="RRG primitives not found in daily_prices"
                    )
                
                return ModelResult(
                    symbol=symbol,
                    model_id=self.id,
                    model_version=self.version,
                    evaluation_date=eval_date,
                    status="SUCCESS",
                    score=None,  # RRG doesn't emit a unified score, it's a vector model
                    payload={
                        "quadrant": row["rrg_quadrant"],
                        "heading": float(row["rrg_heading"]) if row["rrg_heading"] is not None else None,
                        "rs_ratio": float(row["jdk_rs_ratio"]) if row["jdk_rs_ratio"] is not None else None,
                        "rs_momentum": float(row["jdk_rs_momentum"]) if row["jdk_rs_momentum"] is not None else None,
                        "benchmark": row["rrg_benchmark"],
                        "methodology": "MRI_RRG_V1.0",
                        "evaluation_date": eval_date.isoformat(),
                        "data_date": row["date"].isoformat()
                    }
                )
        finally:
            conn.close()
