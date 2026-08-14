from app.services.observation_learning import observation_policy

def test_observation_requires_direction_score_and_entry():
    base={"directional_bias":"LONG","long_score":50,"short_score":1,"entry_decision":{"entry_center":100}}
    assert observation_policy(base)[0] is True
    x=dict(base); x["long_score"]=10
    assert observation_policy(x)[0] is False
    x=dict(base); x["entry_decision"]=None
    assert observation_policy(x)[0] is False

def test_observation_does_not_change_strict_policy():
    from app.services.collector import _policy
    signal={"state":"WATCH","directional_bias":"LONG","signal_quality":{"grade":"LOW","cross_market_long":False},"entry_decision":{"entry_center":100}}
    ok,_=_policy(signal,{"active":0,"waiting_entry":0})
    assert ok is False
