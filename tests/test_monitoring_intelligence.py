import asyncio
import app.services.monitoring as monitoring


def test_monitoring_payload_includes_intelligence(monkeypatch):
    async def fake_snapshot():
        return {
            "symbol": "BTCUSDT", "price": 63000, "primary_source": "OKX",
            "source_degraded": False, "spread_bps": 0.1, "change_24h_pct": 0.0,
            "cross_exchange": {}
        }

    monkeypatch.setattr(monitoring, "build_market_snapshot", fake_snapshot)
    monkeypatch.setattr(monitoring, "calculate_signal", lambda s: {
        "state": "NO_TRADE", "directional_bias": "NONE", "candidate_opportunity": "NONE",
        "long_score": 0, "short_score": 0, "signal_quality": {}, "adaptive_assessment": {},
        "confidence_pct": None, "setup_grade": None, "entry_decision": None,
        "blockers": [], "warnings": []
    })
    monkeypatch.setattr(monitoring, "collector_status", lambda: {})
    monkeypatch.setattr(monitoring, "validation_report", lambda: {"overall": {"resolved": 2}})
    monkeypatch.setattr(monitoring, "build_intelligence", lambda: {"overall": {"resolved": 2}, "dimensions": {}, "leaderboard": []})
    monkeypatch.setattr(monitoring, "recent_validation", lambda limit: [])

    payload = asyncio.run(monitoring.build_monitoring_payload())
    assert payload["intelligence"]["overall"]["resolved"] == 2
