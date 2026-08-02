from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from decimal import Decimal
import datetime

from engine_core.model_results_repository import ModelResult

class InvestmentModel(ABC):
    """
    Base interface for all analytical models in the Investment Model Platform.
    Every model (CANSLIM, RRG, etc.) must implement this contract.
    """
    
    @property
    @abstractmethod
    def id(self) -> str:
        """The unique identifier for this model (e.g., 'CANSLIM', 'RRG')."""
        pass
        
    @property
    @abstractmethod
    def version(self) -> str:
        """The version of this model (e.g., '1.0', '1.2')."""
        pass
        
    @abstractmethod
    def evaluate(self, symbol: str, evaluation_date: Optional[datetime.date] = None) -> ModelResult:
        """
        Evaluate the symbol and return a standardized ModelResult envelope.
        
        If evaluation_date is not provided, the model should use today's date.
        
        Args:
            symbol: The stock ticker symbol.
            evaluation_date: The date for which to run the evaluation.
            
        Returns:
            ModelResult containing the standardized output payload.
        """
        pass
