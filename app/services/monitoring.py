from app.config import settings
from app.services.market import build_market_snapshot
from app.services.engine import calculate_signal
from app.services.validation_analytics import validation_report
from app.services.validation_intelligence import build_intelligence
from app.services.regime_analytics import build_regime_analytics
from app.services.data_health import build_data_health
from app.services.learning_readiness import build_learning_readiness
from app.services.lifecycle_health import lifecycle_health
from app.services.learning_funnel import funnel_stats
from app.services.observation_learning import observation_stats
from app.services.forward_test import forward_test_status
from app.services.regime_prior import regime_prior_summary
from app.services.collector import collector_status
from app.services.validation_storage import recent_validation

async def build_monitoring_payload():
    snapshot = await build_market_snapshot()
    signal = calculate_signal(snapshot)
    collector = collector_status()
    orderflow = snapshot.get("orderflow") or {}
    # V9.6.2: cross_exchange is the canonical venue map. The primary
    # orderflow object contains metrics, not necessarily per-venue children.
    normalized_venues = snapshot.get("cross_exchange") or orderflow.get("venues") or {
        k: orderflow.get(k, {})
        for k in ("bybit","binance","okx","kraken","coinbase")
        if isinstance(orderflow.get(k), dict)
    }
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
        "intelligence": build_intelligence(),
        "regime_analytics": build_regime_analytics(),
        "data_health": build_data_health(snapshot, collector, normalized_venues),
        "learning_readiness": build_learning_readiness(),
        "lifecycle_health": lifecycle_health(),
        "learning_funnel": funnel_stats(24),
        "observation_learning": observation_stats(168),
        "forward_test": forward_test_status(),
        "regime_prior": regime_prior_summary(),
        "validation_acceleration": {
            "enabled": settings.learning_capture_enabled,
            "learning_min_state": settings.learning_capture_min_state,
            "learning_min_score": settings.learning_capture_min_score,
            "allow_low_quality": settings.learning_capture_allow_low_quality,
            "strict_trade_rules_unchanged": True,
        },
    }
