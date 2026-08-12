from app.services.learning_funnel import classify_stage

def test_funnel_stages():
    assert classify_stage(strict_ok=True,learning_ok=True,captured=True,capture_mode="STRICT")=="STRICT_CAPTURE"
    assert classify_stage(strict_ok=False,learning_ok=True,captured=True,capture_mode="LEARNING")=="LEARNING_CAPTURE"
    assert classify_stage(strict_ok=True,learning_ok=True,captured=False,capture_mode=None)=="STRICT_CANDIDATE"
    assert classify_stage(strict_ok=False,learning_ok=True,captured=False,capture_mode=None)=="LEARNING_CANDIDATE"
    assert classify_stage(strict_ok=False,learning_ok=False,captured=False,capture_mode=None)=="REJECTED_NOISE"
