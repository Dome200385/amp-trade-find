from app.config import settings
from app.services.market import build_market_snapshot
from app.services.engine import calculate_signal
from app.services.validation_analytics import validation_report
from app.services.collector import collector_status

async def build_monitoring_payload():
    snapshot = await build_market_snapshot()
    signal = calculate_signal(snapshot)
    return {
        "api_version": settings.app_version,
        "strategy_version": settings.strategy_version,
        "paper_mode": settings.paper_mode,
        "market": {
            "symbol": snapshot.get("symbol"),
            "price": snapshot.get("price"),
            "primary_source": snapshot.get("primary_source"),
            "source_degraded": snapshot.get("source_degraded"),
            "spread_bps": snapshot.get("spread_bps"),
            "change_24h_pct": snapshot.get("change_24h_pct"),
        },
        "signal": {
            "state": signal.get("state"),
            "directional_bias": signal.get("directional_bias"),
            "candidate": signal.get("candidate_opportunity"),
            "long_score": signal.get("long_score"),
            "short_score": signal.get("short_score"),
            "quality": signal.get("signal_quality"),
            "entry_decision": signal.get("entry_decision"),
            "blockers": signal.get("blockers", []),
            "warnings": signal.get("warnings", []),
        },
        "venues": snapshot.get("cross_exchange", {}),
        "collector": collector_status(),
        "validation": validation_report(),
    }
