from __future__ import annotations


def clamp_score(value: float, floor: float = 0, ceiling: float = 100) -> float:
    return max(floor, min(ceiling, value))


def compute_stee_setup_score(mri_snapshot: dict | None) -> float:
    if not mri_snapshot:
        return 0.0

    score = 0.0
    if mri_snapshot.get("condition_breakout_10d"):
        score += 35
    if mri_snapshot.get("condition_price_quality"):
        score += 25
    if mri_snapshot.get("condition_volume"):
        score += 20
    if mri_snapshot.get("condition_ema_50_200"):
        score += 10
    if mri_snapshot.get("condition_rs"):
        score += 10
    return clamp_score(score)


def compute_trajectory_support(quality_snapshot: dict | None) -> float:
    if not quality_snapshot:
        return 0.0

    score_change = float(quality_snapshot.get("score_change") or 0)
    velocity = float(quality_snapshot.get("velocity") or 0)

    support = 50.0
    support += max(-20.0, min(20.0, score_change))
    support += max(-15.0, min(15.0, velocity * 5.0))
    return clamp_score(support)


def compute_fragility_snapshot(
    quality_snapshot: dict | None,
    financial_history: list[dict],
    mri_snapshot: dict | None,
) -> dict:
    reasons: list[str] = []
    score = 0

    if quality_snapshot:
        if float(quality_snapshot.get("score_change") or 0) < 0:
            score += 20
            reasons.append("Quality score is deteriorating versus the prior snapshot.")
        if float(quality_snapshot.get("velocity") or 0) < 0:
            score += 10
            reasons.append("Trajectory velocity has turned negative.")
        if quality_snapshot.get("category") == "REJECT":
            score += 30
            reasons.append("QIF classification is already in the reject bucket.")

    if financial_history:
        latest = financial_history[-1]
        equity = float(latest.get("equity") or 0)
        debt = float(latest.get("debt") or 0)
        if equity > 0:
            debt_to_equity = debt / equity
            if debt_to_equity >= 1.0:
                score += 20
                reasons.append("Balance sheet leverage is elevated versus equity.")
            elif debt_to_equity >= 0.5:
                score += 10
                reasons.append("Balance sheet leverage is worth monitoring.")

    if mri_snapshot:
        technical_score = float(mri_snapshot.get("total_score") or 0)
        if technical_score >= 90 and not mri_snapshot.get("condition_breakout_10d"):
            score += 15
            reasons.append("Technical score is strong, but breakout confirmation is not active.")
        if technical_score < 60:
            score += 15
            reasons.append("Market confirmation is not yet broad-based.")

    fragility_score = clamp_score(score)
    if fragility_score >= 60:
        level = "HIGH"
    elif fragility_score >= 30:
        level = "MODERATE"
    else:
        level = "LOW"

    return {
        "level": level,
        "score": round(fragility_score, 1),
        "reasons": reasons or ["No immediate fragility flags from current deterministic evidence."],
    }


def compute_perx_score(
    mri_snapshot: dict,
    quality_snapshot: dict,
    stee_score: float,
    trajectory_support: float,
    fragility_snapshot: dict,
    forensic_review: dict | None = None,
) -> float:
    mri_score = float(mri_snapshot.get("total_score") or 0)
    qif_score = float(quality_snapshot.get("score") or 0)
    fragility_penalty = float(fragility_snapshot.get("score") or 0) * 0.15

    debate_adjustment = 0.0
    if forensic_review and not forensic_review.get("unavailable"):
        verdict = forensic_review.get("verdict") or {}
        debate_score = verdict.get("score")
        if debate_score is not None:
            debate_adjustment = (float(debate_score) - 5.0) * 2.0

    perx_score = (
        (mri_score * 0.35)
        + (qif_score * 0.40)
        + (stee_score * 0.15)
        + (trajectory_support * 0.10)
        + debate_adjustment
        - fragility_penalty
    )
    return round(clamp_score(perx_score), 1)


def classify_lifecycle_stage(
    perx_score: float,
    mri_snapshot: dict,
    quality_snapshot: dict,
    fragility_snapshot: dict,
) -> str:
    mri_score = float(mri_snapshot.get("total_score") or 0)
    qif_score = float(quality_snapshot.get("score") or 0)
    fragility_level = fragility_snapshot.get("level")

    if perx_score >= 85 and fragility_level == "HIGH":
        return "Euphoria"
    if perx_score >= 82 and mri_score >= 80 and qif_score >= 75:
        return "Institutional Expansion"
    if perx_score >= 72 and mri_score >= 70 and qif_score >= 70:
        return "Early Rerating"
    if perx_score >= 60 and qif_score >= 60:
        return "Accumulation"
    return "Distribution"


def narrative_intensity_label(perx_score: float) -> str:
    if perx_score >= 80:
        return "HIGH"
    if perx_score >= 65:
        return "MEDIUM"
    return "LOW"
