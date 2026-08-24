from app.services.v910_selection import _stats

def test_stats_positive_bucket():
    rows=[{"close_r":1.5,"outcome":"TP1","rr1":1.5},{"close_r":-1.0,"outcome":"STOPPED","rr1":1.5},{"close_r":1.5,"outcome":"TP1","rr1":1.5}]
    s=_stats(rows)
    assert s["n"]==3
    assert s["win_rate_pct"] > 60
    assert s["profit_factor"] == 3.0
    assert s["expectancy_r"] > 0
