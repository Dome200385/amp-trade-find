def _clip(v, lo=0.0, hi=100.0):
    return max(lo, min(hi, float(v)))

def _component_direction(components, name):
    for c in components:
        if c.get("name") == name:
            lp = float(c.get("long_points") or 0)
            sp = float(c.get("short_points") or 0)
            if lp > sp:
                return "LONG"
            if sp > lp:
                return "SHORT"
    return "NEUTRAL"

def build_adaptive_assessment(
    *,
    quality: dict,
    components: list[dict],
    long_score: int,
    short_score: int,
    direction: str,
    timing_matches: bool,
) -> dict:
    directional_score = max(int(long_score), int(short_score))
    separation = abs(int(long_score) - int(short_score))
    available = int(quality.get("available_venues") or 0)

    if direction not in ("LONG", "SHORT"):
        # Still expose a market confidence measure, but do not grade it as a setup.
        confidence = _clip(directional_score * 0.45 + min(separation, 40) * 0.35)
        return {
            "confidence_pct": round(confidence, 1),
            "setup_grade": "UNRATED",
            "direction": "NONE",
            "score_separation": separation,
            "contradictions": ["NO_CLEAR_DIRECTION"],
            "strengths": [],
            "rationale": "No sufficiently separated LONG/SHORT directional bias.",
        }

    confidence = directional_score * 0.52
    confidence += min(separation, 40) * 0.45

    strengths = []
    contradictions = []

    cross_market = (
        quality.get("cross_market_long", False)
        if direction == "LONG"
        else quality.get("cross_market_short", False)
    )
    if cross_market:
        confidence += 14
        strengths.append("SPOT_DERIVATIVES_CONFIRM")
    else:
        confidence -= 8
        contradictions.append("CROSS_MARKET_MISSING")

    qgrade = quality.get("grade")
    if qgrade == "HIGH":
        confidence += 8
        strengths.append("HIGH_SIGNAL_QUALITY")
    elif qgrade == "MEDIUM":
        confidence += 3
        strengths.append("MEDIUM_SIGNAL_QUALITY")
    elif qgrade == "LOW":
        confidence -= 12
        contradictions.append("LOW_SIGNAL_QUALITY")

    cvd_dir = quality.get("live_cvd_direction")
    if cvd_dir == direction:
        confidence += 9
        strengths.append("LIVE_CVD_CONFIRM")
    elif cvd_dir in ("LONG", "SHORT"):
        confidence -= 10
        contradictions.append("LIVE_CVD_OPPOSES")

    if timing_matches:
        confidence += 7
        strengths.append("5M_TIMING_CONFIRM")
    else:
        confidence -= 5
        contradictions.append("5M_TIMING_MISSING")

    trend_1h = _component_direction(components, "1H trend")
    trend_15m = _component_direction(components, "15M trend")
    if trend_1h == direction and trend_15m == direction:
        confidence += 8
        strengths.append("MULTITIMEFRAME_TREND_CONFIRM")
    elif direction in (trend_1h, trend_15m):
        confidence += 2
    elif trend_1h != "NEUTRAL" and trend_15m != "NEUTRAL":
        confidence -= 7
        contradictions.append("MULTITIMEFRAME_TREND_OPPOSES")

    if available >= 3:
        confidence += 4
        strengths.append("THREE_PLUS_VENUES")
    elif available < 2:
        confidence -= 15
        contradictions.append("INSUFFICIENT_VENUES")

    if quality.get("market_conflict"):
        confidence -= 18
        contradictions.append("SPOT_DERIVATIVES_CONFLICT")

    confidence = round(_clip(confidence), 1)

    # Grades are intentionally stricter than raw score.
    if (
        confidence >= 82
        and qgrade == "HIGH"
        and cross_market
        and not quality.get("market_conflict")
    ):
        setup_grade = "A"
    elif confidence >= 70 and qgrade in ("HIGH", "MEDIUM") and not quality.get("market_conflict"):
        setup_grade = "B"
    elif confidence >= 58 and qgrade in ("HIGH", "MEDIUM"):
        setup_grade = "C"
    else:
        setup_grade = "UNRATED"

    if setup_grade == "A":
        rationale = "Strong multi-source alignment with limited contradiction."
    elif setup_grade == "B":
        rationale = "Good setup, but at least one confirmation layer is weaker."
    elif setup_grade == "C":
        rationale = "Directional setup exists, but confirmation quality is only moderate."
    else:
        rationale = "Directional evidence is not strong enough for an A/B/C setup."

    return {
        "confidence_pct": confidence,
        "setup_grade": setup_grade,
        "direction": direction,
        "score_separation": separation,
        "strengths": strengths,
        "contradictions": contradictions,
        "rationale": rationale,
    }
