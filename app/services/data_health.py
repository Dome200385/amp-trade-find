from datetime import datetime, timezone
from app.config import settings

def _venue_status(snapshot: dict):
    venues = snapshot.get("cross_exchange") or {}
    result = {}
    live = 0
    for name, data in venues.items():
        available = bool((data or {}).get("available"))
        if available:
            live += 1
        result[name] = {
            "available": available,
            "market_type": (data or {}).get("market_type"),
            "error": (data or {}).get("error"),
            "delta_pct": (data or {}).get("taker_delta_pct"),
            "orderbook_imbalance": (data or {}).get("orderbook_imbalance"),
        }
    return live, result

def build_data_health(snapshot: dict, collector: dict):
    live_count, venues = _venue_status(snapshot)
    last_cycle = collector.get("last_cycle_at_utc")
    stale = False
    age_seconds = None
    if last_cycle:
        try:
            ts = datetime.fromisoformat(last_cycle.replace("Z","+00:00"))
            age_seconds = (datetime.now(timezone.utc)-ts).total_seconds()
            stale = age_seconds > settings.health_stale_seconds
        except Exception:
            pass

    warnings = []
    if live_count < 3:
        warnings.append("LOW_VENUE_COVERAGE")
    if snapshot.get("source_degraded"):
        warnings.append("PRIMARY_SOURCE_DEGRADED")
    if stale:
        warnings.append("COLLECTOR_STALE")
    if collector.get("last_error"):
        warnings.append("COLLECTOR_ERROR")

    return {
        "status": "DEGRADED" if warnings else "HEALTHY",
        "live_venues": live_count,
        "minimum_recommended_live_venues": 3,
        "primary_source": snapshot.get("primary_source"),
        "source_degraded": bool(snapshot.get("source_degraded")),
        "collector_age_seconds": round(age_seconds,1) if age_seconds is not None else None,
        "collector_stale": stale,
        "warnings": warnings,
        "venues": venues,
    }
