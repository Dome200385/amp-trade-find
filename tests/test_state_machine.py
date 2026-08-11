from app.services.state_machine import transition

def test_low_score_no_trade():
    r = transition(
        candidate_direction="NONE",
        directional_score=20,
        quality_grade="LOW",
        cross_market_confirmed=False,
        live_cvd_matches=False,
        timing_matches=False,
        event_blocked=False,
        blockers=["LOW_SIGNAL_QUALITY"],
        entry_decision=None,
    )
    assert r["state"] == "NO_TRADE"

def test_ready_when_entry_not_here():
    r = transition(
        candidate_direction="LONG",
        directional_score=78,
        quality_grade="HIGH",
        cross_market_confirmed=True,
        live_cvd_matches=True,
        timing_matches=True,
        event_blocked=False,
        blockers=[],
        entry_decision={"valid": True, "entry_now": False},
    )
    assert r["state"] == "READY"
