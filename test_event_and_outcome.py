from datetime import datetime, timezone
from app.services.outcome_evaluator import evaluate_one

def test_long_tp1():
    row = {
        "candidate": "LONG",
        "stop": 99,
        "target1": 102,
        "target2": 104,
        "expires_at": "2099-01-01T00:00:00+00:00",
    }
    assert evaluate_one(row, 102.5) == "TP1"

def test_short_stop():
    row = {
        "candidate": "SHORT",
        "stop": 101,
        "target1": 98,
        "target2": 96,
        "expires_at": "2099-01-01T00:00:00+00:00",
    }
    assert evaluate_one(row, 101.2) == "STOPPED"
