import pandas as pd
import numpy as np

def compute_rrg_indicators(stock_close: pd.Series, benchmark_close: pd.Series, window: int = 14) -> pd.DataFrame:
    """
    MRI RRG Approximation V1.0 - Frozen Methodology.
    
    This is the explicitly documented MRI approximation of the Julius de Kempenaer (JdK) formulas.
    Any changes to this math constitute a major version bump to the RRG model.
    
    Formula V1.0:
    1. RS = stock_close / benchmark_close
    2. JdK RS-Ratio = 100 * (RS / SMA(RS, window))
    3. JdK RS-Momentum = 100 * (RS-Ratio / SMA(RS-Ratio, window))
    4. Quadrants based on standard (100, 100) Cartesian crossover.
    
    Args:
        stock_close: Series of stock close prices.
        benchmark_close: Series of benchmark close prices aligned by date.
        window: The period for moving averages (default 14).
        
    Returns:
        DataFrame containing 'jdk_rs_ratio', 'jdk_rs_momentum', 'rrg_quadrant', 'rrg_heading'
    """
    # 1. Compute Raw Relative Strength (RS)
    rs = stock_close / benchmark_close
    
    # 2. Compute JdK RS-Ratio (Normalized RS)
    # Using 100 * (RS / SMA(RS, window))
    rs_sma = rs.rolling(window=window).mean()
    jdk_rs_ratio = 100 * (rs / rs_sma)
    
    # 3. Compute JdK RS-Momentum (Rate of change of RS-Ratio)
    # Using 100 * (RS-Ratio / SMA(RS-Ratio, window))
    ratio_sma = jdk_rs_ratio.rolling(window=window).mean()
    jdk_rs_momentum = 100 * (jdk_rs_ratio / ratio_sma)
    
    # 4. Map to Quadrants
    # LEADING: Ratio > 100, Momentum > 100
    # WEAKENING: Ratio > 100, Momentum < 100
    # LAGGING: Ratio < 100, Momentum < 100
    # IMPROVING: Ratio < 100, Momentum > 100
    
    conditions = [
        (jdk_rs_ratio > 100) & (jdk_rs_momentum > 100),
        (jdk_rs_ratio > 100) & (jdk_rs_momentum <= 100),
        (jdk_rs_ratio <= 100) & (jdk_rs_momentum <= 100),
        (jdk_rs_ratio <= 100) & (jdk_rs_momentum > 100)
    ]
    choices = ["LEADING", "WEAKENING", "LAGGING", "IMPROVING"]
    
    rrg_quadrant = np.select(conditions, choices, default="UNKNOWN")
    
    # 5. Compute Heading (Angle in degrees)
    # atan2(y - 100, x - 100) gives angle from center
    # Note: atan2 takes (y, x), which maps to (momentum - 100, ratio - 100)
    dy = jdk_rs_momentum - 100
    dx = jdk_rs_ratio - 100
    radians = np.arctan2(dy, dx)
    degrees = np.degrees(radians)
    # Normalize to 0-360
    rrg_heading = np.where(degrees < 0, degrees + 360, degrees)
    
    return pd.DataFrame({
        "jdk_rs_ratio": jdk_rs_ratio,
        "jdk_rs_momentum": jdk_rs_momentum,
        "rrg_quadrant": rrg_quadrant,
        "rrg_heading": rrg_heading
    }, index=stock_close.index)
