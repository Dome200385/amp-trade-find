from app.services.adaptive_quality import build_adaptive_assessment

def comp(name, lp=0, sp=0):
    return {"name":name,"long_points":lp,"short_points":sp,"max_points":10,"detail":""}

def quality(**kw):
    q = {
        "grade":"HIGH","available_venues":3,"cross_market_long":True,
        "cross_market_short":False,"live_cvd_direction":"LONG","market_conflict":False,
    }
    q.update(kw)
    return q

def test_a_grade_for_strong_long():
    a = build_adaptive_assessment(
        quality=quality(),
        components=[comp("1H trend",10,0),comp("15M trend",10,0)],
        long_score=86,short_score=22,direction="LONG",timing_matches=True,
    )
    assert a["setup_grade"] == "A"
    assert a["confidence_pct"] >= 82

def test_conflict_reduces_grade():
    a = build_adaptive_assessment(
        quality=quality(market_conflict=True),
        components=[comp("1H trend",10,0),comp("15M trend",10,0)],
        long_score=80,short_score=30,direction="LONG",timing_matches=True,
    )
    assert a["setup_grade"] != "A"
    assert "SPOT_DERIVATIVES_CONFLICT" in a["contradictions"]

def test_no_direction_is_unrated():
    a = build_adaptive_assessment(
        quality=quality(),
        components=[],long_score=40,short_score=38,direction="NONE",timing_matches=False,
    )
    assert a["setup_grade"] == "UNRATED"
