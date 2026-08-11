from datetime import datetime, timezone
from app.config import settings
from app.services.market import build_market_snapshot
from app.services.engine import calculate_signal
from app.services.storage import performance_stats, recent_signals
from app.services.notification_payload import build_notification_payload
from app.services.validation_analytics import validation_report

def _fmt_event(event_risk: dict) -> dict:
    return {
        "blocked": bool(event_risk.get("blocked", False)),
        "next_event": event_risk.get("next_event"),
        "active_events": event_risk.get("active_events", []),
    }

async def build_dashboard():
    snapshot = await build_market_snapshot()
    signal = calculate_signal(snapshot)
    perf = performance_stats()
    validation = validation_report()
    history = recent_signals(20)

    x = snapshot["cross_exchange"]
    live = snapshot["live_cvd"]
    cvd5 = live.get("cvd_5m", {})

    return {
        "api_version": settings.app_version,
        "strategy_version": settings.strategy_version,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "paper_mode": settings.paper_mode,
        "market": {
            "symbol": snapshot["symbol"],
            "primary_source": snapshot.get("primary_source"),
            "source_degraded": snapshot.get("source_degraded", False),
            "source_errors": snapshot.get("source_errors", {}),
            "price": snapshot["price"],
            "change_24h_pct": snapshot.get("change_24h_pct"),
            "funding_rate": snapshot.get("funding_rate"),
            "spread_bps": snapshot["spread_bps"],
            "bias": signal["market_bias"],
        },
        "signal": {
            "signal_id": signal["signal_id"],
            "state": signal["state"],
            "state_machine": signal.get("state_machine", {}),
            "candidate": signal["candidate_opportunity"],
            "directional_bias": signal.get("directional_bias", "NONE"),
            "long_score": signal["long_score"],
            "short_score": signal["short_score"],
            "setup": signal["setup"],
            "quality": signal.get("signal_quality", {}),
            "blockers": signal["blockers"],
            "warnings": signal.get("warnings", []),
            "entry_decision": signal.get("entry_decision"),
            "trade_plan": signal.get("trade_plan"),
            "components": signal.get("components", []),
        },
        "notification": build_notification_payload(signal, snapshot),
        "orderflow": {
            "primary_source": snapshot.get("primary_source"),
            "primary_delta_pct": snapshot["orderflow"]["taker_delta_pct"],
            "primary_orderbook_imbalance": snapshot["orderflow"]["orderbook_imbalance"],
            "oi_change_pct": snapshot["orderflow"].get("oi_change_pct"),
            "cvd_5m_pct": cvd5.get("delta_pct"),
            "cvd_5m_btc": cvd5.get("cvd_btc"),
            "cvd_connected": live.get("connected", False),
        },
        "venues": {
            "consensus": x["consensus"],
            "strength": x["consensus_strength"],
            "long_confirmations": x["long_confirmations"],
            "short_confirmations": x["short_confirmations"],
            "available": x["available_venues"],
            "available_names": x.get("available_names", []),
            "bybit": x["bybit"],
            "binance": x["binance"],
            "okx": x["okx"],
            "kraken": x["kraken"],
            "coinbase": x["coinbase"],
        },
        "event_risk": _fmt_event(snapshot["event_risk"]),
        "performance": perf,
        "validation": validation,
        "recent_signals": history,
        "disclaimer": "Paper-analysis system. FIND Score is not a guaranteed probability."
    }
