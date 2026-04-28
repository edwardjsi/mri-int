import numpy as np
from typing import List, Optional, Tuple

def compute_score_velocity(history: List[float]) -> float:
    """Compute the rate of improvement (velocity) of scores.
    
    Formula: Avg of period-over-period changes.
    """
    if len(history) < 2:
        return 0.0
    
    # Calculate differences between consecutive scores
    diffs = [history[i] - history[i-1] for i in range(1, len(history))]
    return float(np.mean(diffs))

def detect_score_trend(history: List[float]) -> str:
    """Detect the trajectory trend based on recent history."""
    if len(history) < 3:
        return "insufficient"
    
    recent = history[-3:] # Last 3 scores
    
    if recent[2] > recent[1] > recent[0]:
        return "strong_uptrend"
    elif recent[2] > recent[1]:
        return "uptrend"
    elif recent[2] < recent[1] < recent[0]:
        return "strong_downtrend"
    elif recent[2] < recent[1]:
        return "downtrend"
    return "flat"

def classify_quality_signal(score: float, change: float, velocity: float) -> str:
    """Classify the stock based on absolute quality and trajectory."""
    if score > 75 and change > 5:
        return "BREAKOUT_CANDIDATE"
    if score > 75 and velocity > 3:
        return "RAPID_IMPROVER"
    if score > 60 and velocity > 2:
        return "EMERGING_QUALITY"
    if score < 50 and change > 10:
        return "TURNAROUND"
    if score > 70:
        return "STABLE_QUALITY"
    return "WATCH"
