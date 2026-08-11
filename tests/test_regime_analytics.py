from app.services.regime_analytics import _stats

def test_regime_stats():
    rows=[
      {"outcome":"TP1","close_r":1.5,"rr1":1.5},
      {"outcome":"STOPPED","close_r":-1.0,"rr1":1.5},
      {"outcome":"ACTIVE","close_r":None,"rr1":1.5},
    ]
    s=_stats(rows)
    assert s["resolved"]==2
    assert s["win_rate_pct"]==50.0
    assert s["expectancy_r"]==0.25
