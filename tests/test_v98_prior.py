from app.services.regime_prior import _stats, _adjustment

def test_prior_stats():
    rows=[{"outcome":"TP1","close_r":1.5,"rr1":1.5},{"outcome":"STOPPED","close_r":-1.0,"rr1":1.5}]
    s=_stats(rows)
    assert s["resolved"]==2
    assert s["win_rate_pct"]==50.0
    assert s["expectancy_r"]==0.25

def test_adjustment_requires_sample():
    assert _adjustment({"resolved":10,"expectancy_r":1,"profit_factor":3,"win_rate_pct":70})==0
