from __future__ import annotations
from datetime import datetime, timezone
from statistics import pstdev

def _component(signal: dict, name: str):
    for c in signal.get("components", []) or []:
        if c.get("name") == name:
            return c
    return {}

def _direction_from_component(c: dict):
    lp = float(c.get("long_points") or 0)
    sp = float(c.get("short_points") or 0)
    if lp > sp: return "LONG"
    if sp > lp: return "SHORT"
    return "NEUTRAL"

def _volatility_bucket(snapshot: dict):
    # Prefer explicit ATR/volatility if later added by market layer.
    for key in ("atr_pct", "volatility_pct", "realized_volatility_pct"):
        val = snapshot.get(key)
        if val is not None:
            try:
                v = float(val)
                if v >= 2.0: return "HIGH", v
                if v >= 0.9: return "MEDIUM", v
                return "LOW", v
            except Exception:
                pass

    change = snapshot.get("change_24h_pct")
    try:
        v = abs(float(change))
        if v >= 4.0: return "HIGH", v
        if v >= 1.5: return "MEDIUM", v
        return "LOW", v
    except Exception:
        return "UNKNOWN", None

def _market_regime(signal: dict, snapshot: dict):
    one_h = _direction_from_component(_component(signal, "1H trend"))
    m15 = _direction_from_component(_component(signal, "15M trend"))
    bias = signal.get("directional_bias") or "NONE"
    quality = signal.get("signal_quality") or {}
    conflict = bool(quality.get("market_conflict"))
    cross = quality.get("overall_consensus") or "NEUTRAL"
    vol_bucket, _ = _volatility_bucket(snapshot)

    if conflict:
        return "CONFLICT"
    if one_h == m15 and one_h in ("LONG", "SHORT"):
        if vol_bucket == "HIGH":
            return f"TRENDING_{one_h}_HIGH_VOL"
        return f"TRENDING_{one_h}"
    if one_h != "NEUTRAL" and m15 != "NEUTRAL" and one_h != m15:
        return "CHOPPY"
    if bias in ("LONG", "SHORT") and cross == bias:
        return f"EARLY_{bias}"
    return "RANGE_NEUTRAL"

def extract_setup_features(snapshot: dict, signal: dict) -> dict:
    quality = signal.get("signal_quality") or {}
    adaptive = signal.get("adaptive_assessment") or {}
    orderflow = snapshot.get("orderflow") or {}
    vol_bucket, vol_value = _volatility_bucket(snapshot)

    one_h = _direction_from_component(_component(signal, "1H trend"))
    m15 = _direction_from_component(_component(signal, "15M trend"))
    vwap = _direction_from_component(_component(signal, "VWAP"))
    rsi = _component(signal, "RSI14").get("detail")
    timing = _component(signal, "5M timing").get("detail")

    now = datetime.now(timezone.utc)

    return {
        "captured_hour_utc": now.hour,
        "captured_weekday_utc": now.weekday(),
        "market_regime": _market_regime(signal, snapshot),
        "volatility_bucket": vol_bucket,
        "volatility_value": vol_value,
        "trend_1h": one_h,
        "trend_15m": m15,
        "vwap_bias": vwap,
        "rsi_detail": rsi,
        "timing_detail": timing,
        "cross_market_consensus": quality.get("overall_consensus"),
        "market_conflict": bool(quality.get("market_conflict")),
        "live_cvd_direction": quality.get("live_cvd_direction"),
        "live_cvd_pct": quality.get("live_cvd_pct"),
        "available_venues": quality.get("available_venues"),
        "primary_source": snapshot.get("primary_source"),
        "source_degraded": bool(snapshot.get("source_degraded")),
        "spread_bps": snapshot.get("spread_bps"),
        "change_24h_pct": snapshot.get("change_24h_pct"),
        "funding_rate": snapshot.get("funding_rate"),
        "primary_delta_pct": orderflow.get("primary_delta_pct"),
        "primary_orderbook_imbalance": orderflow.get("primary_orderbook_imbalance"),
        "score_long": signal.get("long_score"),
        "score_short": signal.get("short_score"),
        "confidence_pct": signal.get("confidence_pct") or adaptive.get("confidence_pct"),
        "setup_grade": signal.get("setup_grade") or adaptive.get("setup_grade"),
    }
