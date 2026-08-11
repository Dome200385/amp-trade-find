from dataclasses import dataclass
from app.config import settings

@dataclass
class EntryDecision:
    direction: str
    entry_low: float
    entry_high: float
    stop: float
    target1: float
    target2: float
    rr1: float
    rr2: float
    invalidation: str
    valid: bool
    reason: str

def _round(v):
    return round(float(v), 2)

def _support_resistance(snapshot: dict, direction: str):
    t5 = snapshot["tf_5m"]
    t15 = snapshot["tf_15m"]
    price = float(snapshot["price"])

    # V8.4 uses indicator structure as an initial proxy.
    # V8.5 can replace this with explicit swing-high/low and liquidity zones.
    if direction == "LONG":
        support = max(
            min(float(t5["ema20"]), price),
            min(float(t15["ema20"]), price),
            min(float(t15["vwap"]), price),
        )
        resistance = max(price, float(t5["ema20"]), float(t15["ema20"]), float(t15["vwap"]))
        return support, resistance

    resistance = min(
        max(float(t5["ema20"]), price),
        max(float(t15["ema20"]), price),
        max(float(t15["vwap"]), price),
    )
    support = min(price, float(t5["ema20"]), float(t15["ema20"]), float(t15["vwap"]))
    return support, resistance

def build_entry_decision(snapshot: dict, direction: str) -> dict:
    price = float(snapshot["price"])
    atr = max(float(snapshot["tf_15m"]["atr14"]), price * 0.001)
    zone = atr * settings.entry_zone_atr_fraction
    stop_dist = atr * settings.stop_atr_multiplier

    support, resistance = _support_resistance(snapshot, direction)

    if direction == "LONG":
        entry_center = max(support, price - zone * 0.5)
        entry_low = entry_center - zone
        entry_high = entry_center + zone
        structural_stop = min(support - atr * 0.15, price - stop_dist)
        stop = min(structural_stop, entry_low - atr * 0.10)
        risk = max(entry_center - stop, atr * 0.5)
        target1 = entry_center + risk * settings.min_rr_target1
        target2 = entry_center + risk * settings.min_rr_target2
        invalidation = (
            f"15M close below {_round(stop)} or loss of support/VWAP structure"
        )
    else:
        entry_center = min(resistance, price + zone * 0.5)
        entry_low = entry_center - zone
        entry_high = entry_center + zone
        structural_stop = max(resistance + atr * 0.15, price + stop_dist)
        stop = max(structural_stop, entry_high + atr * 0.10)
        risk = max(stop - entry_center, atr * 0.5)
        target1 = entry_center - risk * settings.min_rr_target1
        target2 = entry_center - risk * settings.min_rr_target2
        invalidation = (
            f"15M close above {_round(stop)} or reclaim of resistance/VWAP structure"
        )

    rr1 = abs(target1 - entry_center) / risk if risk else 0.0
    rr2 = abs(target2 - entry_center) / risk if risk else 0.0

    # Sanity checks.
    valid = True
    reasons = []

    if rr1 < settings.min_rr_target1 - 0.01:
        valid = False
        reasons.append("RR1_TOO_LOW")
    if rr2 < settings.min_rr_target2 - 0.01:
        valid = False
        reasons.append("RR2_TOO_LOW")
    if not (entry_low <= price <= entry_high):
        # Not an error: this means setup is valid but entry has not arrived yet.
        reasons.append("WAITING_FOR_ENTRY_ZONE")

    return {
        "direction": direction,
        "entry_low": _round(entry_low),
        "entry_high": _round(entry_high),
        "entry_center": _round(entry_center),
        "stop": _round(stop),
        "target1": _round(target1),
        "target2": _round(target2),
        "rr_target1": round(rr1, 2),
        "rr_target2": round(rr2, 2),
        "invalidation": invalidation,
        "validity_minutes": settings.setup_expiry_minutes,
        "valid": valid,
        "entry_now": entry_low <= price <= entry_high,
        "reason": ",".join(reasons) if reasons else "READY",
    }
