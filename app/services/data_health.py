from datetime import datetime, timezone
from app.config import settings

KNOWN_VENUES = ("bybit","binance","okx","kraken","coinbase")

def _extract_venues(snapshot: dict):
    # V9.x snapshots may expose venues either directly under cross_exchange
    # or nested in orderflow. Support both.
    venues = snapshot.get("cross_exchange")
    if isinstance(venues, dict) and venues:
        return venues

    orderflow = snapshot.get("orderflow") or {}
    nested = orderflow.get("venues")
    if isinstance(nested, dict) and nested:
        return nested

    # Fallback: construct from named venue keys in snapshot/orderflow.
    result = {}
    for name in KNOWN_VENUES:
        data = snapshot.get(name)
        if not isinstance(data, dict):
            data = orderflow.get(name)
        if isinstance(data, dict):
            result[name] = data
    return result

def _venue_available(data: dict):
    if not isinstance(data, dict):
        return False
    if data.get("available") is True:
        return True
    # Some existing payloads omit available but have real market data.
    if data.get("error"):
        return False
    meaningful = (
        data.get("trade_count"),
        data.get("taker_delta_pct"),
        data.get("orderbook_imbalance"),
        data.get("market_type"),
    )
    return any(v not in (None, 0, 0.0, "") for v in meaningful)

def build_data_health(snapshot: dict, collector: dict):
    venues = _extract_venues(snapshot)
    venue_status = {}
    live_count = 0

    for name in KNOWN_VENUES:
        data = venues.get(name) or venues.get(name.upper()) or {}
        available = _venue_available(data)
        if available:
            live_count += 1
        venue_status[name] = {
            "available": available,
            "market_type": data.get("market_type"),
            "error": data.get("error"),
            "delta_pct": data.get("taker_delta_pct"),
            "orderbook_imbalance": data.get("orderbook_imbalance"),
        }

    last_cycle = collector.get("last_cycle_at_utc")
    stale = False
    age_seconds = None
    if last_cycle:
        try:
            ts = datetime.fromisoformat(str(last_cycle).replace("Z","+00:00"))
            age_seconds = max(0.0, (datetime.now(timezone.utc)-ts).total_seconds())
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
        "venues": venue_status,
    }
