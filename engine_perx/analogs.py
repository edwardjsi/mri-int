def get_historical_analogs(perx_score: float, lifecycle: str) -> list[str]:
    """Identify 1-2 historical Indian stocks with similar trajectories."""
    # Simplified rule-based analogs for V3
    if perx_score >= 80 and lifecycle == "Institutional Expansion":
        return ["POLYCAB (2021)", "HAL (2022)"]
    if perx_score >= 70:
        return ["KEI (2020)", "APL APOLLO (2021)"]
    if perx_score >= 60:
        return ["BEL (2021)", "SIEMENS (2022)"]
    return ["Watchlist candidates under evaluation"]
