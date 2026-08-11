from app.config import settings
from app.services.market import build_market_snapshot
from app.services.engine import calculate_signal
from app.services.validation_analytics import validation_report
from app.services.validation_intelligence import build_intelligence
from app.services.regime_analytics import build_regime_analytics
from app.services.data_health import build_data_health
from app.services.learning_readiness import build_learning_readiness
from app.services.lifecycle_health import lifecycle_health
from app.services.collector import collector_status
from app.services.validation_storage import recent_validation

async def build_monitoring_payload():
    snapshot = await build_market_snapshot()
    signal = calculate_signal(snapshot)
    collector = collector_status()
    normalized_venues = (
        snapshot.get("cross_exchange")
        or (snapshot.get("orderflow") or {}).get("venues")
        or {
            k:(snapshot.get("orderflow") or {}).get(k,{})
            for k in ("bybit","binance","okx","kraken","coinbase")
        }
    )
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
            "adaptive": signal.get("adaptive_assessment"),
            "confidence_pct": signal.get("confidence_pct"),
            "setup_grade": signal.get("setup_grade"),
            "entry_decision": signal.get("entry_decision"),
            "blockers": signal.get("blockers", []),
            "warnings": signal.get("warnings", []),
        },
        "venues": normalized_venues,
        "collector": collector,
        "validation": validation_report(),
        "recent_setups": recent_validation(8),
    }
