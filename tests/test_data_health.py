from app.services.data_health import build_data_health

def test_data_health_degraded_when_low_venues():
    snapshot={
      "primary_source":"OKX","source_degraded":False,
      "cross_exchange":{
        "okx":{"available":True},
        "kraken":{"available":True},
        "coinbase":{"available":False},
      }
    }
    collector={"last_cycle_at_utc":None,"last_error":None}
    h=build_data_health(snapshot,collector)
    assert h["status"]=="DEGRADED"
    assert "LOW_VENUE_COVERAGE" in h["warnings"]
