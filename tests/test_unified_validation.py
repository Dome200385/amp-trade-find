from app.services.unified_validation import normalized_outcome, r_value

def test_normalize():
    assert normalized_outcome("STOP")=="STOPPED"
    assert normalized_outcome("TARGET1")=="TP1"
    assert normalized_outcome("ACTIVE")=="ACTIVE"

def test_r_reconstruction():
    assert r_value({"outcome":"TP1","close_r":None,"rr1":1.5})==1.5
    assert r_value({"outcome":"STOPPED","close_r":None,"rr1":1.5})==-1.0
