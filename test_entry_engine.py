from app.services.entry_engine import build_entry_decision

def snapshot(price=100.0):
    return {
        "price": price,
        "tf_5m": {"ema20": 99.8, "ema50": 99.5, "vwap": 99.7, "atr14": 1.0},
        "tf_15m": {"ema20": 99.5, "ema50": 99.0, "vwap": 99.6, "atr14": 1.2},
    }

def test_long_entry_has_positive_rr():
    p = build_entry_decision(snapshot(), "LONG")
    assert p["stop"] < p["entry_center"]
    assert p["target1"] > p["entry_center"]
    assert p["rr_target1"] >= 1.49

def test_short_entry_has_positive_rr():
    s = snapshot()
    s["tf_5m"]["ema20"] = 100.2
    s["tf_15m"]["ema20"] = 100.5
    s["tf_15m"]["vwap"] = 100.4
    p = build_entry_decision(s, "SHORT")
    assert p["stop"] > p["entry_center"]
    assert p["target1"] < p["entry_center"]
    assert p["rr_target1"] >= 1.49
