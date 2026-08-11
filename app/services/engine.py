from datetime import datetime, timezone
from app.config import settings

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
        "direction": direction, "entry": round(price, 2), "stop": round(stop, 2),
        "target1": round(t1, 2), "target2": round(t2, 2),
        "rr_target1": 1.5, "rr_target2": 2.2, "validity_minutes": 15,
    }

def calculate_signal(snapshot: dict) -> dict:
    t5, t15, t1h = snapshot["tf_5m"], snapshot["tf_15m"], snapshot["tf_1h"]
    of, x = snapshot["orderflow"], snapshot["cross_exchange"]
    live = snapshot["live_cvd"]
    event = snapshot["event_risk"]
    price = snapshot["price"]
    c = []

    # Core technical + Bybit microstructure = 80 points
    if t1h["ema20"] > t1h["ema50"]: c.append(_component("1H trend", 10, 0, 10, "Bullish"))
    elif t1h["ema20"] < t1h["ema50"]: c.append(_component("1H trend", 0, 10, 10, "Bearish"))
    else: c.append(_component("1H trend", 0, 0, 10, "Neutral"))

    if t15["ema20"] > t15["ema50"]: c.append(_component("15M trend", 10, 0, 10, "Bullish"))
    elif t15["ema20"] < t15["ema50"]: c.append(_component("15M trend", 0, 10, 10, "Bearish"))
    else: c.append(_component("15M trend", 0, 0, 10, "Neutral"))

    if price > t15["vwap"]: c.append(_component("VWAP", 8, 0, 8, "Above"))
    elif price < t15["vwap"]: c.append(_component("VWAP", 0, 8, 8, "Below"))
    else: c.append(_component("VWAP", 0, 0, 8, "At VWAP"))

    rsi = t15["rsi14"]
    if 52 <= rsi <= 70: c.append(_component("RSI14", 5, 0, 5, f"{rsi:.1f} bullish"))
    elif 30 <= rsi <= 48: c.append(_component("RSI14", 0, 5, 5, f"{rsi:.1f} bearish"))
    else: c.append(_component("RSI14", 0, 0, 5, f"{rsi:.1f} mixed/extreme"))

    vr = t15["volume_ratio"]
    if vr >= 1.15 and price > t15["ema20"]: c.append(_component("Volume", 5, 0, 5, f"{vr:.2f}x"))
    elif vr >= 1.15 and price < t15["ema20"]: c.append(_component("Volume", 0, 5, 5, f"{vr:.2f}x"))
    else: c.append(_component("Volume", 0, 0, 5, f"{vr:.2f}x"))

    if t5["ema20"] > t5["ema50"] and price > t5["vwap"]: c.append(_component("5M timing", 8, 0, 8, "Long confirms"))
    elif t5["ema20"] < t5["ema50"] and price < t5["vwap"]: c.append(_component("5M timing", 0, 8, 8, "Short confirms"))
    else: c.append(_component("5M timing", 0, 0, 8, "Mixed"))

    dp = of["taker_delta_pct"]
    if dp >= 8: c.append(_component("Bybit taker delta", 12, 0, 12, f"+{dp:.1f}%"))
    elif dp <= -8: c.append(_component("Bybit taker delta", 0, 12, 12, f"{dp:.1f}%"))
    else: c.append(_component("Bybit taker delta", 0, 0, 12, f"{dp:.1f}%"))

    imb = of["orderbook_imbalance"]
    if imb >= .10: c.append(_component("Bybit orderbook", 8, 0, 8, f"{imb:.2f}"))
    elif imb <= -.10: c.append(_component("Bybit orderbook", 0, 8, 8, f"{imb:.2f}"))
    else: c.append(_component("Bybit orderbook", 0, 0, 8, f"{imb:.2f}"))

    oi_chg = of.get("oi_change_pct")
    if oi_chg is not None and oi_chg >= .08 and dp > 0:
        c.append(_component("OI confirmation", 7, 0, 7, f"+{oi_chg:.3f}% with buying"))
    elif oi_chg is not None and oi_chg >= .08 and dp < 0:
        c.append(_component("OI confirmation", 0, 7, 7, f"+{oi_chg:.3f}% with selling"))
    else:
        c.append(_component("OI confirmation", 0, 0, 7, f"{oi_chg if oi_chg is not None else 'n/a'}"))

    funding = snapshot.get("funding_rate")
    if funding is not None and funding <= .0005:
        c.append(_component("Funding long sanity", 4, 0, 4, f"{funding:.5f}"))
    else: c.append(_component("Funding long sanity", 0, 0, 4, str(funding)))
    if funding is not None and funding >= -.0005:
        c.append(_component("Funding short sanity", 0, 3, 3, f"{funding:.5f}"))
    else: c.append(_component("Funding short sanity", 0, 0, 3, str(funding)))

    # Rolling live CVD is a hard-quality confirmation, not extra score inflation.
    cvd5 = live.get("cvd_5m", {})
    cvd5_pct = float(cvd5.get("delta_pct", 0) or 0)
    live_ready = bool(live.get("connected")) and int(cvd5.get("trade_count", 0) or 0) >= 25
    if live_ready and cvd5_pct >= 5:
        c.append(_component("Live 5M CVD", 0, 0, 0, f"Live CVD confirms LONG {cvd5_pct:.1f}%"))
    elif live_ready and cvd5_pct <= -5:
        c.append(_component("Live 5M CVD", 0, 0, 0, f"Live CVD confirms SHORT {cvd5_pct:.1f}%"))
    else:
        c.append(_component("Live 5M CVD", 0, 0, 0, f"Live CVD not ready/neutral {cvd5_pct:.1f}%"))

    # Cross-exchange consensus = 20 points
    if x["consensus"] == "LONG":
        pts = 20 if x["long_confirmations"] >= 3 else 14
        c.append(_component("Cross-exchange consensus", pts, 0, 20,
                            f'{x["long_confirmations"]}/{x["available_venues"]} venues LONG'))
    elif x["consensus"] == "SHORT":
        pts = 20 if x["short_confirmations"] >= 3 else 14
        c.append(_component("Cross-exchange consensus", 0, pts, 20,
                            f'{x["short_confirmations"]}/{x["available_venues"]} venues SHORT'))
    else:
        c.append(_component("Cross-exchange consensus", 0, 0, 20,
                            f'{x["consensus"]}; {x["available_venues"]} venues available'))

    long_score = min(100, sum(z["long_points"] for z in c))
    short_score = min(100, sum(z["short_points"] for z in c))

    if long_score - short_score >= 18 and long_score >= 50: bias = "BULLISH"
    elif short_score - long_score >= 18 and short_score >= 50: bias = "BEARISH"
    else: bias = "NEUTRAL"

    mandatory_long = (
        bias == "BULLISH" and dp >= 8 and t5["ema20"] > t5["ema50"]
        and x["consensus"] == "LONG" and x["long_confirmations"] >= 2
        and live_ready and cvd5_pct >= 5 and not event.get("blocked", False)
    )
    mandatory_short = (
        bias == "BEARISH" and dp <= -8 and t5["ema20"] < t5["ema50"]
        and x["consensus"] == "SHORT" and x["short_confirmations"] >= 2
        and live_ready and cvd5_pct <= -5 and not event.get("blocked", False)
    )

    candidate = "NONE"
    if long_score >= settings.signal_threshold and mandatory_long: candidate = "LONG"
    elif short_score >= settings.signal_threshold and mandatory_short: candidate = "SHORT"

    top = max(long_score, short_score)
    state = "SETUP_FORMING" if candidate != "NONE" or top >= settings.setup_threshold else (
        "MARKET_WATCH" if top >= settings.watch_threshold else "NO_TRADE"
    )

    blockers = ["PAPER_MODE", "BACKTEST_NOT_VALIDATED"]
    if not live_ready:
        blockers.append("LIVE_CVD_NOT_READY")
    if event.get("blocked", False):
        blockers.append("HIGH_IMPACT_EVENT")
    if x["available_venues"] < 2: blockers.append("INSUFFICIENT_VENUES")
    if snapshot["spread_bps"] > 5: blockers.append("WIDE_SPREAD")

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
        "setup": "Cross-exchange momentum candidate" if bias != "NEUTRAL" else "None",
        "components": c,
        "blockers": blockers,
        "trade_plan": _trade_plan(snapshot, candidate) if candidate in ("LONG", "SHORT") else None,
        "paper_mode": True,
        "note": (
            "V4 combines cross-exchange flow, rolling Bybit CVD, event blocking and automatic outcome tracking. "
            "Live trade alerts remain blocked until the validation sample gate and strategy review are passed."
        ),
    }
