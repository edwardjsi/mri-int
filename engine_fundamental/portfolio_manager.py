from typing import Dict, List, Optional

def compute_portfolio_decision(score: float, velocity: float, trend: str) -> str:
    """Determine hold/sell/reduce decisions based on trajectory."""
    if score > 75 and velocity > 2:
        return "STRONG_HOLD"
    if score > 65 and velocity > 0:
        return "HOLD"
    if score < 60 and trend in ["downtrend", "strong_downtrend"]:
        return "REDUCE"
    if score < 50:
        return "EXIT"
    return "WATCH"

def compute_position_size(score: float, velocity: float, total_capital: float) -> Dict:
    """Calculate the ideal position size based on Kelly-inspired quality weighting."""
    base_weight = 0.0
    
    # Absolute Score Weighting
    if score > 80:
        base_weight = 0.10 # Max 10%
    elif score > 70:
        base_weight = 0.07
    elif score > 60:
        base_weight = 0.05
    else:
        base_weight = 0.02
        
    # Velocity Multiplier
    if velocity > 3:
        base_weight += 0.02
    elif velocity > 5:
        base_weight += 0.03
        
    # Safety Cap
    final_weight = min(0.12, base_weight) # Absolute cap of 12% per position
    allocation = total_capital * final_weight
    
    return {
        "weight": round(final_weight, 3),
        "allocation": round(allocation, 2)
    }

def check_portfolio_drawdown(current_value: float, peak_value: float) -> str:
    """Portfolio-level risk protection logic."""
    if peak_value <= 0:
        return "NORMAL"
        
    drawdown = (peak_value - current_value) / peak_value
    
    if drawdown > 0.25:
        return "FULL_RISK_OFF"
    elif drawdown > 0.15:
        return "REDUCE_EXPOSURE"
    elif drawdown > 0.10:
        return "CAUTION"
    return "NORMAL"
