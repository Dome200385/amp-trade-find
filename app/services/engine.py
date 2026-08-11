from datetime import datetime, timezone
from app.config import settings
from app.services.signal_quality import build_signal_quality
from app.services.entry_engine import build_entry_decision
from app.services.state_machine import transition
from app.services.adaptive_quality import build_adaptive_assessment

def _component(name: str, lp: int, sp: int, mx: int, detail: str) -> dict:
    return {"name": name, "long_points": lp, "short_points": sp, "max_points": mx, "detail": detail}

def calculate_signal(snapshot: dict) -> dict:
    t5, t15, t1h = snapshot["tf_5m"], snapshot["tf_15m"], snapshot["tf_1h"]
    of, x = snapshot["orderflow"], snapshot["cross_exchange"]
    live, event = snapshot["live_cvd"], snapshot["event_risk"]
    quality = build_signal_quality(x, live)
    price = float(snapshot["price"])
    c = []

    # ----- Trend & timing -----
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

    rsi = float(t15["rsi14"])
    if 52 <= rsi <= 70:
        c.append(_component("RSI14", 5, 0, 5, f"{rsi:.1f} bullish"))
    elif 30 <= rsi <= 48:
        c.append(_component("RSI14", 0, 5, 5, f"{rsi:.1f} bearish"))
    else:
        c.append(_component("RSI14", 0, 0, 5, f"{rsi:.1f} mixed/extreme"))

    vr = float(t15["volume_ratio"])
    if vr >= 1.15 and price > t15["ema20"]:
        c.append(_component("Volume", 5, 0, 5, f"{vr:.2f}x"))
    elif vr >= 1.15 and price < t15["ema20"]:
        c.append(_component("Volume", 0, 5, 5, f"{vr:.2f}x"))
    else:
        c.append(_component("Volume", 0, 0, 5, f"{vr:.2f}x"))

    timing_long = t5["ema20"] > t5["ema50"] and price > t5["vwap"]
    timing_short = t5["ema20"] < t5["ema50"] and price < t5["vwap"]

    if timing_long:
        c.append(_component("5M timing", 8, 0, 8, "Long confirms"))
    elif timing_short:
        c.append(_component("5M timing", 0, 8, 8, "Short confirms"))
    else:
        c.append(_component("5M timing", 0, 0, 8, "Mixed"))

    # ----- Microstructure -----
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

    # ----- Cross-market quality -----
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
        c.append(_component("Cross-exchange consensus", 10, 0, 20, "LONG but cross-market confirmation incomplete"))
    elif x["consensus"] == "SHORT" and quality["grade"] == "MEDIUM":
        c.append(_component("Cross-exchange consensus", 0, 10, 20, "SHORT but cross-market confirmation incomplete"))
    else:
        c.append(_component(
            "Cross-exchange consensus", 0, 0, 20,
            f'{x["consensus"]}; quality {quality["grade"]}; {x["available_venues"]} venues'
        ))

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

    # Directional bias.
    if long_score - short_score >= 18 and long_score >= 50:
        bias = "BULLISH"
        direction = "LONG"
        directional_score = long_score
    elif short_score - long_score >= 18 and short_score >= 50:
        bias = "BEARISH"
        direction = "SHORT"
        directional_score = short_score
    else:
        bias = "NEUTRAL"
        direction = "NONE"
        directional_score = max(long_score, short_score)

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

    warnings = []
    if snapshot.get("source_degraded"):
        warnings.append(f'PRIMARY_SOURCE_FALLBACK_{snapshot.get("primary_source","UNKNOWN")}')
    for venue_name in (snapshot.get("source_errors") or {}).keys():
        warnings.append(f'{venue_name}_REST_UNAVAILABLE')

    cross_confirm = (
        quality["cross_market_long"] if direction == "LONG"
        else quality["cross_market_short"] if direction == "SHORT"
        else False
    )
    cvd_matches = cvd_direction == direction if direction in ("LONG", "SHORT") else False
    timing_matches = timing_long if direction == "LONG" else timing_short if direction == "SHORT" else False

    entry = build_entry_decision(snapshot, direction) if direction in ("LONG", "SHORT") else None

    adaptive = build_adaptive_assessment(
        quality=quality,
        components=c,
        long_score=long_score,
        short_score=short_score,
        direction=direction,
        timing_matches=timing_matches,
    )

    state = transition(
        candidate_direction=direction,
        directional_score=directional_score,
        quality_grade=quality["grade"],
        cross_market_confirmed=cross_confirm,
        live_cvd_matches=cvd_matches,
        timing_matches=timing_matches,
        event_blocked=bool(event.get("blocked", False)),
        blockers=blockers,
        entry_decision=entry,
    )

    candidate = direction if state["state"] == "PAPER_SIGNAL" else "NONE"

    signal_id = "FIND-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    return {
        "signal_id": signal_id,
        "symbol": snapshot["symbol"],
        "price": price,
        "state": state["state"],
        "state_machine": state,
        "candidate_opportunity": candidate,
        "directional_bias": direction,
        "long_score": int(long_score),
        "short_score": int(short_score),
        "market_bias": bias,
        "setup": "Cross-market momentum candidate" if direction != "NONE" else "None",
        "signal_quality": quality,
        "adaptive_assessment": adaptive,
        "confidence_pct": adaptive["confidence_pct"],
        "setup_grade": adaptive["setup_grade"],
        "entry_decision": entry,
        "components": c,
        "blockers": blockers,
        "warnings": warnings,
        "trade_plan": entry if candidate in ("LONG", "SHORT") else None,
        "paper_mode": True,
        "note": (
            "V9.2 adds adaptive confidence and A/B/C grading while retaining the state machine. "
            "quality, live CVD, timing and entry-zone conditions all align."
        ),
    }
