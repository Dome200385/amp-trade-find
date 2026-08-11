from app.services.setup_features import extract_setup_features

def test_features_basic():
    snapshot={"primary_source":"OKX","change_24h_pct":2.1,"source_degraded":False,"orderflow":{}}
    signal={
      "directional_bias":"LONG","long_score":80,"short_score":20,
      "signal_quality":{"overall_consensus":"LONG","available_venues":3,"market_conflict":False},
      "components":[
        {"name":"1H trend","long_points":10,"short_points":0},
        {"name":"15M trend","long_points":10,"short_points":0},
      ]
    }
    f=extract_setup_features(snapshot,signal)
    assert f["market_regime"].startswith("TRENDING_LONG")
    assert f["volatility_bucket"]=="MEDIUM"
    assert f["trend_1h"]=="LONG"
