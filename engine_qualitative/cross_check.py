def cross_check(q_score, agent_results):
    penalties = 0
    flags = []

    # Handle both list of dicts or dict of scores
    if isinstance(agent_results, list):
        scores = {a["agent_name"]: a["score"] for a in agent_results}
    else:
        scores = agent_results

    # pricing claim vs margins
    if q_score >= 7 and scores.get("margin_quality", 5) < 5:
        penalties += 2
        flags.append("narrative_margin_mismatch")

    # demand claim vs working capital
    if q_score >= 7 and scores.get("working_capital", 7) < 4:
        penalties += 2
        flags.append("narrative_wc_mismatch")

    return penalties, flags
