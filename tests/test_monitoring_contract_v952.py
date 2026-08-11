import asyncio
import app.services.monitoring as mon

def test_monitoring_contains_health_learning_modules(monkeypatch):
    snapshot = {
        "symbol":"BTCUSDT","price":63000,"primary_source":"OKX","source_degraded":False,
        "orderflow":{
            "okx":{"available":True,"market_type":"SWAP","taker_delta_pct":1.0},
            "kraken":{"available":True,"market_type":"SPOT","taker_delta_pct":2.0},
            "coinbase":{"available":True,"market_type":"SPOT","taker_delta_pct":3.0},
            "bybit":{"available":False,"market_type":"FUTURES","error":"off"},
            "binance":{"available":False,"market_type":"FUTURES","error":"off"},
        }
    }
    async def fake_snapshot(): return snapshot
    monkeypatch.setattr(mon,"build_market_snapshot",fake_snapshot)
    monkeypatch.setattr(mon,"calculate_signal",lambda s:{
        "state":"NO_TRADE","directional_bias":"NONE","candidate_opportunity":None,
        "long_score":0,"short_score":0,"signal_quality":{},"adaptive_assessment":{},
        "confidence_pct":0,"setup_grade":"UNRATED","entry_decision":None,
        "blockers":[],"warnings":[]
    })
    monkeypatch.setattr(mon,"collector_status",lambda:{"last_cycle_at_utc":None,"last_error":None})
    monkeypatch.setattr(mon,"validation_report",lambda:{})
    monkeypatch.setattr(mon,"recent_validation",lambda n:[])
    monkeypatch.setattr(mon,"build_intelligence",lambda:{"overall":{"resolved":2}})
    monkeypatch.setattr(mon,"build_regime_analytics",lambda:{"overall":{"captured":3}})
    monkeypatch.setattr(mon,"build_learning_readiness",lambda:{"overall":{"resolved":2}})
    monkeypatch.setattr(mon,"lifecycle_health",lambda:{"active":1,"resolved":2,"healthy":True})

    d=asyncio.run(mon.build_monitoring_payload())
    assert d["data_health"]["live_venues"] == 3
    assert d["intelligence"]["overall"]["resolved"] == 2
    assert d["learning_readiness"]["overall"]["resolved"] == 2
    assert d["lifecycle_health"]["active"] == 1
    assert d["lifecycle_health"]["resolved"] == 2
