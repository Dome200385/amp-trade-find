from app.config import settings
from app.services.validation_intelligence import build_intelligence
from app.services.regime_analytics import build_regime_analytics

def _level(n):
    if n >= settings.learning_min_samples_strong:
        return "STRONG"
    if n >= settings.learning_min_samples_usable:
        return "USABLE"
    if n >= settings.learning_min_samples_warning:
        return "EARLY"
    return "INSUFFICIENT"

def build_learning_readiness():
    intel = build_intelligence()
    regime = build_regime_analytics()

    # Source of truth: validation intelligence overall resolved.
    resolved = int((intel.get("overall") or {}).get("resolved") or 0)
    readiness = _level(resolved)

    regime_rows = []
    for name, stats in (regime.get("dimensions", {}).get("market_regime", {}) or {}).items():
        n = int(stats.get("resolved") or 0)
        regime_rows.append({
            "regime": name,
            "resolved": n,
            "readiness": _level(n),
            "expectancy_r": stats.get("expectancy_r"),
            "profit_factor": stats.get("profit_factor"),
            "win_rate_pct": stats.get("win_rate_pct"),
        })
    regime_rows.sort(key=lambda x:(x["resolved"], x["regime"]), reverse=True)

    return {
        "overall": {
            "resolved": resolved,
            "readiness": readiness,
            "thresholds": {
                "early": settings.learning_min_samples_warning,
                "usable": settings.learning_min_samples_usable,
                "strong": settings.learning_min_samples_strong,
            }
        },
        "regimes": regime_rows[:12],
        "recommendation": (
            "Do not optimize strategy rules yet."
            if readiness in ("INSUFFICIENT","EARLY")
            else "Begin controlled hypothesis testing only in PAPER_MODE."
            if readiness == "USABLE"
            else "Sample size supports controlled strategy refinement."
        ),
    }
