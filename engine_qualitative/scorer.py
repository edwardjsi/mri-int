def score_signals(signals):
    score = 5
    flags = []

    for s in signals:
        t, p = s.get("type"), s.get("polarity")

        if t == "pricing_power" and p == "positive":
            score += 2
        if t == "cost_pressure" and p == "negative":
            score -= 1
            flags.append("cost_pressure")
        if t == "working_capital" and p == "negative":
            score -= 2
            flags.append("wc_risk")

    score = max(0, min(10, score))
    return score, flags
