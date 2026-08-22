from app.services.forward_diagnostics import _stats

def test_v99_stats():
    stats = _stats([
        {"outcome": "TP1", "close_r": 1.5, "rr1": 1.5},
        {"outcome": "STOPPED", "close_r": -1.0, "rr1": 1.5},
        {"outcome": "STOPPED", "close_r": -1.0, "rr1": 1.5},
    ])
    assert stats["resolved"] == 3
    assert round(stats["expectancy_r"], 3) == -0.167
