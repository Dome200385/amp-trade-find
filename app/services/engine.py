from datetime import datetime, timezone
from app.config import settings
from app.services.signal_quality import build_signal_quality

def _component(name: str, lp: int, sp: int, mx: int, detail: str) -> dict:
    return {"name": name, "long_points": lp, "short_points": sp, "max_points": mx, "detail": detail}

def _trade_plan(snapshot: dict, direction: str) -> dict:
    price = snapshot["price"]
    atr = max(snapshot["tf_15m"]["atr14"], price * 0.001)
    stop_distance = atr * 1.15
    if direction == "LONG":
        stop, t1, t2 = price - stop_distance, price + stop_distance * 1.5, price + stop_distance * 2.2
    else:
        stop, t1, t2 = price + stop_distance, price - stop_distance * 1.5, price - stop_distance * 2.2

    return {
        "direction": direction,
        "entry": round(price, 2),
        "stop": round(stop, 2),
        "target1": round(t1, 2),
        "target2": round(t2, 2),
        "rr_target1": 1.5,
        "rr_target2": 2.2,
        "validity_minutes": 15,
    }

def calculate_signal(snapshot: dict) -> dict:
    t5, t15, t1h = snapshot["tf_5m"], snapshot["tf_15m"], snapshot["tf_1h"]
    of, x = snapshot["orderflow"], snapshot["cross_exchange"]
    live, event = snapshot["live_cvd"], snapshot["event_risk"]
    quality = build_signal_quality(x, live)
    price = snapshot["price"]
    c = []

    # Technical layer.
    if t1h["ema20"] > t1h["ema50"]:
        c.append(_component("1H trend", 10, 0, 10, "Bullish"))
    elif t1h["ema20"] < t1h["ema50"]:
        c.append(_component("1H trend", 0, 10, 10, "Bearish"))
    else:
        c.append(_component("1H trend", 0, 0, 10, "Neutral"))

    if t15["ema20"] > t15["ema50"]:
        c.append(_component("15M trend", 10, 0, 10, "Bullish"))
    elif t15["ema20"] < t15["ema50"]:
        c.append(_component("15M trend", 0, 10, 10, "Bearish"))
    else:
        c.append(_component("15M trend", 0, 0, 10, "Neutral"))

    if price > t15["vwap"]:
        c.append(_component("VWAP", 8, 0, 8, "Above"))
    elif price < t15["vwap"]:
        c.append(_component("VWAP", 0, 8, 8, "Below"))
    else:
        c.append(_component("VWAP", 0, 0, 8, "At VWAP"))

    rsi = t15["rsi14"]
    if 52 <= rsi <= 70:
        c.append(_component("RSI14", 5, 0, 5, f"{rsi:.1f} bullish"))
    elif 30 <= rsi <= 48:
        c.append(_component("RSI14", 0, 5, 5, f"{rsi:.1f} bearish"))
    else:
        c.append(_component("RSI14", 0, 0, 5, f"{rsi:.1f} mixed/extreme"))

    vr = t15["volume_ratio"]
    if vr >= 1.15 and price > t15["ema20"]:
        c.append(_component("Volume", 5, 0, 5, f"{vr:.2f}x"))
    elif vr >= 1.15 and price < t15["ema20"]:
        c.append(_component("Volume", 0, 5, 5, f"{vr:.2f}x"))
    else:
        c.append(_component("Volume", 0, 0, 5, f"{vr:.2f}x"))

    if t5["ema20"] > t5["ema50"] and price > t5["vwap"]:
        c.append(_component("5M timing", 8, 0, 8, "Long confirms"))
    elif t5["ema20"] < t5["ema50"] and price < t5["vwap"]:
        c.append(_component("5M timing", 0, 8, 8, "Short confirms"))
    else:
        c.append(_component("5M timing", 0, 0, 8, "Mixed"))

    # Primary-source microstructure.
    dp = float(of.get("taker_delta_pct") or 0)
    if dp >= 8:
        c.append(_component("Primary taker delta", 10, 0, 10, f"+{dp:.1f}%"))
    elif dp <= -8:
        c.append(_component("Primary taker delta", 0, 10, 10, f"{dp:.1f}%"))
    else:
        c.append(_component("Primary taker delta", 0, 0, 10, f"{dp:.1f}%"))

    imb = float(of.get("orderbook_imbalance") or 0)
    if imb >= .10:
        c.append(_component("Primary orderbook", 6, 0, 6, f"{imb:.2f}"))
    elif imb <= -.10:
        c.append(_component("Primary orderbook", 0, 6, 6, f"{imb:.2f}"))
    else:
        c.append(_component("Primary orderbook", 0, 0, 6, f"{imb:.2f}"))

    # OI + funding are derivatives context, not mandatory when primary is spot.
    oi_chg = of.get("oi_change_pct")
    if oi_chg is not None and oi_chg >= .08 and dp > 0:
        c.append(_component("OI confirmation", 5, 0, 5, f"+{oi_chg:.3f}% with buying"))
    elif oi_chg is not None and oi_chg >= .08 and dp < 0:
        c.append(_component("OI confirmation", 0, 5, 5, f"+{oi_chg:.3f}% with selling"))
    else:
        c.append(_component("OI confirmation", 0, 0, 5, f"{oi_chg if oi_chg is not None else 'n/a'}"))

    funding = snapshot.get("funding_rate")
    if funding is not None and funding <= .0005:
        c.append(_component("Funding long sanity", 3, 0, 3, f"{funding:.5f}"))
    else:
        c.append(_component("Funding long sanity", 0, 0, 3, str(funding)))
    if funding is not None and funding >= -.0005:
        c.append(_component("Funding short sanity", 0, 2, 2, f"{funding:.5f}"))
    else:
        c.append(_component("Funding short sanity", 0, 0, 2, str(funding)))

    # Cross-market quality carries more weight than one venue.
    if quality["cross_market_long"] and quality["grade"] == "HIGH":
        c.append(_component(
            "Spot + derivatives agreement", 20, 0, 20,
            f'Derivatives LONG {quality["derivatives"]["long_confirmations"]}; '
            f'Spot LONG {quality["spot"]["long_confirmations"]}'
        ))
    elif quality["cross_market_short"] and quality["grade"] == "HIGH":
        c.append(_component(
            "Spot + derivatives agreement", 0, 20, 20,
            f'Derivatives SHORT {quality["derivatives"]["short_confirmations"]}; '
            f'Spot SHORT {quality["spot"]["short_confirmations"]}'
        ))
    elif x["consensus"] == "LONG" and quality["grade"] == "MEDIUM":
        c.append(_component("Cross-exchange consensus", 10, 0, 20, "LONG but not cross-market HIGH quality"))
    elif x["consensus"] == "SHORT" and quality["grade"] == "MEDIUM":
        c.append(_component("Cross-exchange consensus", 0, 10, 20, "SHORT but not cross-market HIGH quality"))
    else:
        c.append(_component(
            "Cross-exchange consensus", 0, 0, 20,
            f'{x["consensus"]}; quality {quality["grade"]}; {x["available_venues"]} venues'
        ))

    # Live Bybit CVD: hard confirmation, not score inflation.
    cvd_direction = quality["live_cvd_direction"]
    cvd_pct = quality["live_cvd_pct"]
    if cvd_direction == "LONG":
        c.append(_component("Live 5M CVD", 0, 0, 0, f"LONG {cvd_pct:.1f}%"))
    elif cvd_direction == "SHORT":
        c.append(_component("Live 5M CVD", 0, 0, 0, f"SHORT {cvd_pct:.1f}%"))
    else:
        c.append(_component("Live 5M CVD", 0, 0, 0, f"Neutral/not ready {cvd_pct:.1f}%"))

    long_score = min(100, sum(z["long_points"] for z in c))
    short_score = min(100, sum(z["short_points"] for z in c))

    if long_score - short_score >= 18 and long_score >= 50:
        bias = "BULLISH"
    elif short_score - long_score >= 18 and short_score >= 50:
        bias = "BEARISH"
    else:
        bias = "NEUTRAL"

    # V8.3 requires HIGH cross-market agreement for an actual paper candidate.
    mandatory_long = (
        bias == "BULLISH"
        and quality["grade"] == "HIGH"
        and quality["cross_market_long"]
        and quality["live_cvd_ready"]
        and cvd_direction == "LONG"
        and t5["ema20"] > t5["ema50"]
        and not event.get("blocked", False)
    )
    mandatory_short = (
        bias == "BEARISH"
        and quality["grade"] == "HIGH"
        and quality["cross_market_short"]
        and quality["live_cvd_ready"]
        and cvd_direction == "SHORT"
        and t5["ema20"] < t5["ema50"]
        and not event.get("blocked", False)
    )

    candidate = "NONE"
    if long_score >= settings.signal_threshold and mandatory_long:
        candidate = "LONG"
    elif short_score >= settings.signal_threshold and mandatory_short:
        candidate = "SHORT"

    top = max(long_score, short_score)
    if candidate != "NONE":
        state = "SETUP_FORMING"
    elif top >= settings.setup_threshold and quality["grade"] in ("HIGH", "MEDIUM"):
        state = "SETUP_FORMING"
    elif top >= settings.watch_threshold:
        state = "MARKET_WATCH"
    else:
        state = "NO_TRADE"

    blockers = ["PAPER_MODE", "BACKTEST_NOT_VALIDATED"]
    if not quality["live_cvd_ready"]:
        blockers.append("LIVE_CVD_NOT_READY")
    if event.get("blocked", False):
        blockers.append("HIGH_IMPACT_EVENT")
    if quality["available_venues"] < 2:
        blockers.append("INSUFFICIENT_VENUES")
    if quality["grade"] == "LOW":
        blockers.append("LOW_SIGNAL_QUALITY")
    if quality["market_conflict"]:
        blockers.append("SPOT_DERIVATIVES_CONFLICT")
    if quality["grade"] == "MEDIUM" and x["consensus"] in ("LONG", "SHORT"):
        blockers.append("CROSS_MARKET_CONFIRMATION_MISSING")
    if snapshot["spread_bps"] > 5:
        blockers.append("WIDE_SPREAD")

    # Source fallback is now informational, never a blocker by itself.
    warnings = []
    if snapshot.get("source_degraded"):
        warnings.append(f'PRIMARY_SOURCE_FALLBACK_{snapshot.get("primary_source","UNKNOWN")}')
    for venue_name, err in (snapshot.get("source_errors") or {}).items():
        warnings.append(f'{venue_name}_REST_UNAVAILABLE')

    signal_id = "FIND-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    return {
        "signal_id": signal_id,
        "symbol": snapshot["symbol"],
        "price": price,
        "state": state,
        "candidate_opportunity": candidate,
        "long_score": int(long_score),
        "short_score": int(short_score),
        "market_bias": bias,
        "setup": "Cross-market momentum candidate" if bias != "NEUTRAL" else "None",
        "signal_quality": quality,
        "components": c,
        "blockers": blockers,
        "warnings": warnings,
        "trade_plan": _trade_plan(snapshot, candidate) if candidate in ("LONG", "SHORT") else None,
        "paper_mode": True,
        "note": (
            "V8.3 requires independent spot + derivatives confirmation plus matching live CVD "
            "before a paper LONG/SHORT candidate can be created."
        ),
    }
