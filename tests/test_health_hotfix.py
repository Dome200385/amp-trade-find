from app.services.data_health import build_data_health

def test_cross_exchange_live_count():
    snapshot = {
        "primary_source":"OKX",
        "source_degraded":False,
        "cross_exchange":{
            "okx":{"available":True,"market_type":"SWAP","taker_delta_pct":1.0},
            "kraken":{"available":True,"market_type":"SPOT","taker_delta_pct":2.0},
            "coinbase":{"available":True,"market_type":"SPOT","taker_delta_pct":3.0},
            "bybit":{"available":False,"error":"403"},
            "binance":{"available":False,"error":"451"},
        }
    }
    h = build_data_health(snapshot, {"last_cycle_at_utc":None,"last_error":None})
    assert h["live_venues"] == 3
    assert h["status"] == "HEALTHY"

def test_named_venue_fallback():
    snapshot = {
        "primary_source":"OKX",
        "source_degraded":False,
        "okx":{"available":True,"market_type":"SWAP"},
        "kraken":{"available":True,"market_type":"SPOT"},
        "coinbase":{"available":True,"market_type":"SPOT"},
    }
    h = build_data_health(snapshot, {"last_cycle_at_utc":None,"last_error":None})
    assert h["live_venues"] == 3
