from datetime import datetime, timezone
from app.config import settings

KNOWN_VENUES=("bybit","binance","okx","kraken","coinbase")

def _is_live(data):
    if not isinstance(data,dict): return False
    if data.get("available") is True: return True
    if data.get("error"): return False
    return bool(data.get("market_type") and (
        data.get("taker_delta_pct") is not None or
        data.get("orderbook_imbalance") is not None or
        data.get("trade_count") is not None))

def build_data_health(snapshot: dict, collector: dict, normalized_venues: dict | None = None):
    # Cross-exchange is the authoritative orderflow/venue view. Do not confuse
    # the primary ticker fallback with venue orderflow availability.
    venues = normalized_venues or snapshot.get("cross_exchange") or {}
    if not venues:
        venues={name:(snapshot.get(name) or {}) for name in KNOWN_VENUES if isinstance(snapshot.get(name),dict)}
    primary=str(snapshot.get("primary_source") or "").lower()
    source_errors={str(k).lower():v for k,v in (snapshot.get("source_errors") or {}).items()}
    status={}; live=0
    for name in KNOWN_VENUES:
        data=venues.get(name) or venues.get(name.upper()) or {}
        orderflow_live=_is_live(data)
        if orderflow_live: live+=1
        # Primary source proves REST/ticker bundle availability even when a
        # separate cross-market capability is unavailable.
        rest_bundle_live=(name==primary) or (name not in source_errors and orderflow_live)
        status[name]={
            "available":orderflow_live,
            "market_type":data.get("market_type"),
            "error":data.get("error") or source_errors.get(name),
            "delta_pct":data.get("taker_delta_pct"),
            "orderbook_imbalance":data.get("orderbook_imbalance"),
            "capabilities":{
                "primary_price_feed": name==primary,
                "rest_bundle": bool(rest_bundle_live),
                "cross_exchange_orderflow": bool(orderflow_live),
            }
        }
    last_cycle=collector.get("last_cycle_at_utc"); age=None; stale=False
    if last_cycle:
        try:
            ts=datetime.fromisoformat(str(last_cycle).replace("Z","+00:00")); age=max(0,(datetime.now(timezone.utc)-ts).total_seconds()); stale=age>settings.health_stale_seconds
        except Exception: pass
    warnings=[]
    if live<3: warnings.append("LOW_VENUE_COVERAGE")
    if snapshot.get("source_degraded"): warnings.append("PRIMARY_SOURCE_FALLBACK")
    if stale: warnings.append("COLLECTOR_STALE")
    if collector.get("last_error"): warnings.append("COLLECTOR_ERROR")
    return {"status":"DEGRADED" if warnings else "HEALTHY","live_venues":live,"minimum_recommended_live_venues":3,
            "primary_source":snapshot.get("primary_source"),"source_degraded":bool(snapshot.get("source_degraded")),
            "collector_age_seconds":round(age,1) if age is not None else None,"collector_stale":stale,"warnings":warnings,"venues":status}
