import time
import datetime
import logging
from typing import List

from engine_core.investment_model import InvestmentModel
from engine_core.model_results_repository import ModelResult, ModelResultRepository
from engine_core.rrg_model import RrgModel
from engine_core.canslim_model import CanslimModel

logger = logging.getLogger(__name__)

# The global registry of all active investment models.
MODEL_REGISTRY: List[InvestmentModel] = [
    RrgModel(),
    CanslimModel()
]


class ModelRunner:
    """
    Executes all registered models across a universe of symbols.
    It knows nothing about the internal logic of the models.
    """
    def __init__(self, repository: ModelResultRepository, models: List[InvestmentModel] = None):
        """
        Initialize the runner. 
        If models is not provided, defaults to the global MODEL_REGISTRY.
        """
        self.repository = repository
        self.models = models if models is not None else MODEL_REGISTRY

    def run(self, symbols: List[str], evaluation_date: datetime.date = None) -> None:
        """
        Execute every registered model for every symbol in the given universe.
        Catches and records failures gracefully without stopping the batch.
        """
        eval_date = evaluation_date or datetime.date.today()

        for symbol in symbols:
            for model in self.models:
                start_time = time.time()
                
                try:
                    # Model evaluation should return a well-formed ModelResult
                    result = model.evaluate(symbol, eval_date)
                    
                    # Ensure execution metrics are attached
                    execution_ms = int((time.time() - start_time) * 1000)
                    result = ModelResult(
                        symbol=result.symbol,
                        model_id=result.model_id,
                        model_version=result.model_version,
                        evaluation_date=result.evaluation_date,
                        status=result.status,
                        score=result.score,
                        payload=result.payload,
                        explain_node_id=result.explain_node_id,
                        execution_ms=execution_ms,
                        error_message=result.error_message
                    )
                    
                except Exception as e:
                    execution_ms = int((time.time() - start_time) * 1000)
                    error_msg = str(e)
                    logger.error(f"Model {model.id} failed for {symbol}: {error_msg}")
                    
                    # Create a FAILED result envelope
                    result = ModelResult(
                        symbol=symbol,
                        model_id=model.id,
                        model_version=model.version,
                        evaluation_date=eval_date,
                        status="FAILED",
                        score=None,
                        payload=None,
                        execution_ms=execution_ms,
                        error_message=error_msg
                    )

                # Persist to repository
                self.repository.save(result)
