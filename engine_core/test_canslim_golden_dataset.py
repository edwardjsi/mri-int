import os
import sys

sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))
from engine_core.canslim_model import CanslimModel

def test_canslim_golden_dataset():
    """
    Deterministic regression test for the CANSLIM model logic.
    Ensures that the quant mapping functions continue to map primitives correctly 
    to the expected C-A-N-S-L-I-M verdicts without querying the DB.
    """
    model = CanslimModel()
    
    # Static input matching the regression contract
    static_input = {
        "symbol": "GRANULES",
        "regime": "BULLISH",
        "condition_rs": True,
        "condition_6m_high": True,
        "condition_volume": False,
        "condition_ema_200_slope": True,
        "quality_score": 82.5
    }
    
    result = model.evaluate_candidate(static_input)
    comps = result["components"]
    
    # Verify deterministic output
    assert comps["Growth"]["status"] == "PASS", f"Expected Growth PASS, got {comps['Growth']['status']}"
    assert comps["Quality"]["status"] == "PASS", f"Expected Quality PASS, got {comps['Quality']['status']}"
    assert comps["Momentum"]["status"] == "PASS", f"Expected Momentum PASS, got {comps['Momentum']['status']}"
    assert comps["Leadership"]["status"] == "PASS", f"Expected Leadership PASS, got {comps['Leadership']['status']}"
    assert comps["Market"]["status"] == "PASS", f"Expected Market PASS, got {comps['Market']['status']}"
    assert comps["Catalyst"]["status"] == "UNKNOWN", "Expected Catalyst UNKNOWN"
    assert comps["Institutional"]["status"] == "UNKNOWN", "Expected Institutional UNKNOWN"
    
    # Failing case test
    failing_input = {
        "symbol": "BADCO",
        "regime": "BEARISH",
        "condition_rs": False,
        "condition_6m_high": False,
        "condition_volume": False,
        "condition_ema_200_slope": False,
        "quality_score": 40.0
    }
    
    fail_result = model.evaluate_candidate(failing_input)
    f_comps = fail_result["components"]
    
    assert f_comps["Growth"]["status"] == "FAIL"
    assert f_comps["Market"]["status"] == "FAIL"
    
    print("✅ Golden CANSLIM Dataset Test Passed - Deterministic Assertions Verified")

if __name__ == "__main__":
    test_canslim_golden_dataset()
