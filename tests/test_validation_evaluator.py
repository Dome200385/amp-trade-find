from datetime import datetime, timezone, timedelta
from app.services.validation_evaluator import evaluate_row

def row(direction="LONG", entry_reached=0):
    now = datetime.now(timezone.utc)
    return {
        "direction": direction,
        "entry_low": 99.0,
        "entry_high": 101.0,
        "entry_center": 100.0,
        "stop": 98.0 if direction=="LONG" else 102.0,
        "target1": 103.0 if direction=="LONG" else 97.0,
        "target2": 104.4 if direction=="LONG" else 95.6,
        "rr1": 1.5,
        "rr2": 2.2,
        "created_at": (now-timedelta(minutes=1)).isoformat(),
        "entry_reached": entry_reached,
        "entry_fill_price": 100.0 if entry_reached else None,
        "entry_reached_at": (now-timedelta(minutes=1)).isoformat() if entry_reached else None,
        "mfe_price": 100.0,
        "mae_price": 100.0,
    }

def test_entry_activation():
    r = evaluate_row(row(), 100.2)
    assert r["outcome"] == "ACTIVE"
    assert r["entry_reached"] is True

def test_long_stop():
    r = evaluate_row(row(entry_reached=1), 97.9)
    assert r["outcome"] == "STOPPED"
    assert r["close_r"] == -1.0

def test_short_tp1():
    r0 = row("SHORT", 1)
    r = evaluate_row(r0, 96.9)
    assert r["outcome"] == "TP1"
    assert r["close_r"] == 1.5
