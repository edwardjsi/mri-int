import pytest
import datetime
from decimal import Decimal
from typing import Optional

from engine_core.model_results_repository import ModelResult
from engine_core.investment_model import InvestmentModel
from engine_core.model_runner import ModelRunner


class MockRepository:
    def __init__(self):
        self.saved_results = []

    def save(self, result: ModelResult):
        self.saved_results.append(result)


class AlwaysPassModel(InvestmentModel):
    @property
    def id(self) -> str:
        return "PASS_MODEL"

    @property
    def version(self) -> str:
        return "1.0"

    def evaluate(self, symbol: str, evaluation_date: Optional[datetime.date] = None) -> ModelResult:
        eval_date = evaluation_date or datetime.date.today()
        return ModelResult(
            symbol=symbol,
            model_id=self.id,
            model_version=self.version,
            evaluation_date=eval_date,
            status="PASS",
            score=Decimal('100.0'),
            payload={"reason": "Always passes"},
            explain_node_id=None
        )


class AlwaysFailModel(InvestmentModel):
    @property
    def id(self) -> str:
        return "FAIL_MODEL"

    @property
    def version(self) -> str:
        return "2.1"

    def evaluate(self, symbol: str, evaluation_date: Optional[datetime.date] = None) -> ModelResult:
        # Simulate an unexpected crash in the model logic
        raise ValueError("Simulated unexpected crash")


def test_model_runner_orchestration():
    repository = MockRepository()
    models = [AlwaysPassModel(), AlwaysFailModel()]
    runner = ModelRunner(repository=repository, models=models)
    
    symbols = ["TCS", "RELIANCE"]
    eval_date = datetime.date(2026, 8, 3)
    
    runner.run(symbols, evaluation_date=eval_date)
    
    saved = repository.saved_results
    assert len(saved) == 4  # 2 symbols * 2 models
    
    # Check TCS - PASS_MODEL
    tcs_pass = next(r for r in saved if r.symbol == "TCS" and r.model_id == "PASS_MODEL")
    assert tcs_pass.status == "PASS"
    assert tcs_pass.score == Decimal('100.0')
    assert tcs_pass.error_message is None
    assert tcs_pass.execution_ms is not None
    
    # Check TCS - FAIL_MODEL (Should be caught by runner)
    tcs_fail = next(r for r in saved if r.symbol == "TCS" and r.model_id == "FAIL_MODEL")
    assert tcs_fail.status == "FAILED"
    assert tcs_fail.score is None
    assert tcs_fail.error_message == "Simulated unexpected crash"
    assert tcs_fail.execution_ms is not None
    
    # Check RELIANCE - PASS_MODEL
    rel_pass = next(r for r in saved if r.symbol == "RELIANCE" and r.model_id == "PASS_MODEL")
    assert rel_pass.status == "PASS"
    
    # Check RELIANCE - FAIL_MODEL
    rel_fail = next(r for r in saved if r.symbol == "RELIANCE" and r.model_id == "FAIL_MODEL")
    assert rel_fail.status == "FAILED"
