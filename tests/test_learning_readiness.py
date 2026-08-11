from app.services.learning_readiness import _level

def test_learning_levels():
    assert _level(0)=="INSUFFICIENT"
    assert _level(10)=="EARLY"
    assert _level(30)=="USABLE"
    assert _level(100)=="STRONG"
