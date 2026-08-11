from app.config import settings
from app.services.regime_analytics import build_regime_analytics
from app.services.validation_intelligence import build_intelligence

def _level(n):
    if n >= settings.learning_min_samples_strong:
        return "STRONG"
    if n >= settings.learning_min_samples_usable:
        return "USABLE"
    if n >= settings.learning_min_samples_warning:
        return "EARLY"
    return "INSUFFICIENT"

def build_learning_readiness():
    regime = build_regime_analytics()
    intel = build_intelligence()

    resolved = int((intel.get("overall") or {}).get("resolved") or 0)
    grade = _level(resolved)

    regime_readiness = []
    for name, stats in (regime.get("dimensions", {}).get("market_regime", {}) or {}).items():
        n = int(stats.get("resolved") or 0)
        regime_readiness.append({
            "regime": name,
            "resolved": n,
            "readiness": _level(n),
            "expectancy_r": stats.get("expectancy_r"),
            "profit_factor": stats.get("profit_factor"),
            "win_rate_pct": stats.get("win_rate_pct"),
        })
    regime_readiness.sort(key=lambda x:x["resolved"], reverse=True)

    return {
        "overall": {
            "resolved": resolved,
            "readiness": grade,
            "thresholds": {
                "early": settings.learning_min_samples_warning,
                "usable": settings.learning_min_samples_usable,
                "strong": settings.learning_min_samples_strong,
            },
        },
        "regimes": regime_readiness[:12],
        "recommendation": (
            "Do not optimize strategy rules yet."
            if grade in ("INSUFFICIENT","EARLY")
            else "Begin hypothesis testing, but keep changes isolated and paper-only."
            if grade == "USABLE"
            else "Data volume is large enough for controlled strategy refinement."
        ),
    }
