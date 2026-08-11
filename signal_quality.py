DERIVATIVE_TYPES = {"FUTURES", "SWAP"}
SPOT_TYPES = {"SPOT"}

def venue_direction(v: dict) -> str:
    if not v.get("available"):
        return "UNAVAILABLE"

    delta = float(v.get("taker_delta_pct") or 0)
    imb = v.get("orderbook_imbalance")
    imb = float(imb) if imb is not None else 0.0

    # Require both aggressive flow and resting-book support.
    if delta >= 5 and imb >= 0.03:
        return "LONG"
    if delta <= -5 and imb <= -0.03:
        return "SHORT"
    return "NEUTRAL"

def _group_consensus(venues: list[dict]) -> dict:
    active = [v for v in venues if v.get("available")]
    directions = [venue_direction(v) for v in active]
    longs = directions.count("LONG")
    shorts = directions.count("SHORT")

    if longs and shorts:
        consensus = "MIXED"
    elif longs >= 1 and shorts == 0:
        consensus = "LONG"
    elif shorts >= 1 and longs == 0:
        consensus = "SHORT"
    else:
        consensus = "NEUTRAL"

    return {
        "consensus": consensus,
        "long_confirmations": longs,
        "short_confirmations": shorts,
        "available": len(active),
        "venues": [
            {
                "venue": v.get("venue"),
                "market_type": v.get("market_type"),
                "direction": venue_direction(v),
                "delta_pct": v.get("taker_delta_pct"),
                "orderbook_imbalance": v.get("orderbook_imbalance"),
            }
            for v in active
        ],
    }

def build_signal_quality(cross_exchange: dict, live_cvd: dict) -> dict:
    venues = [
        cross_exchange.get("bybit", {}),
        cross_exchange.get("binance", {}),
        cross_exchange.get("okx", {}),
        cross_exchange.get("kraken", {}),
        cross_exchange.get("coinbase", {}),
    ]

    derivatives = [v for v in venues if v.get("market_type") in DERIVATIVE_TYPES]
    spot = [v for v in venues if v.get("market_type") in SPOT_TYPES]

    derivative = _group_consensus(derivatives)
    spot_group = _group_consensus(spot)

    overall = cross_exchange.get("consensus", "NEUTRAL")
    cvd5 = live_cvd.get("cvd_5m", {})
    cvd_pct = float(cvd5.get("delta_pct", 0) or 0)
    cvd_ready = bool(live_cvd.get("connected")) and int(cvd5.get("trade_count", 0) or 0) >= 25
    cvd_direction = "LONG" if cvd_ready and cvd_pct >= 5 else (
        "SHORT" if cvd_ready and cvd_pct <= -5 else "NEUTRAL"
    )

    cross_market_long = (
        derivative["long_confirmations"] >= 1
        and spot_group["long_confirmations"] >= 1
        and derivative["short_confirmations"] == 0
        and spot_group["short_confirmations"] == 0
    )
    cross_market_short = (
        derivative["short_confirmations"] >= 1
        and spot_group["short_confirmations"] >= 1
        and derivative["long_confirmations"] == 0
        and spot_group["long_confirmations"] == 0
    )

    available = int(cross_exchange.get("available_venues", 0) or 0)
    conflicts = (
        derivative["consensus"] == "MIXED"
        or spot_group["consensus"] == "MIXED"
        or (
            derivative["consensus"] in ("LONG", "SHORT")
            and spot_group["consensus"] in ("LONG", "SHORT")
            and derivative["consensus"] != spot_group["consensus"]
        )
    )

    if available >= 3 and (cross_market_long or cross_market_short) and not conflicts:
        grade = "HIGH"
    elif available >= 2 and overall in ("LONG", "SHORT") and not conflicts:
        grade = "MEDIUM"
    elif available >= 2:
        grade = "LOW"
    else:
        grade = "INSUFFICIENT"

    return {
        "grade": grade,
        "available_venues": available,
        "overall_consensus": overall,
        "derivatives": derivative,
        "spot": spot_group,
        "cross_market_long": cross_market_long,
        "cross_market_short": cross_market_short,
        "market_conflict": conflicts,
        "live_cvd_ready": cvd_ready,
        "live_cvd_direction": cvd_direction,
        "live_cvd_pct": round(cvd_pct, 3),
    }
