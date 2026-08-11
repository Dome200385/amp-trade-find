from app.services.validation_auto import _passes_capture_policy

def sig(state="SETUP_FORMING", direction="LONG", grade="HIGH", cross=True, entry=True):
    return {
        "state": state,
        "directional_bias": direction,
        "signal_quality": {
            "grade": grade,
            "cross_market_long": cross if direction=="LONG" else False,
            "cross_market_short": cross if direction=="SHORT" else False,
        },
        "entry_decision": {"valid":True} if entry else None,
    }

def test_auto_policy_accepts_high_quality_setup():
    ok, reason = _passes_capture_policy(sig())
    assert ok is True
    assert reason == "POLICY_OK"

def test_auto_policy_rejects_no_cross_market():
    ok, reason = _passes_capture_policy(sig(cross=False))
    assert ok is False
    assert "CROSS_MARKET" in reason

def test_auto_policy_rejects_low_state():
    ok, reason = _passes_capture_policy(sig(state="WATCH"))
    assert ok is False
    assert "STATE_BELOW" in reason
