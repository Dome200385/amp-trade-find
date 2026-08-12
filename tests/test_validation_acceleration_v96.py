from app.services.collector import _policy, _learning_policy

def sig(state='WATCH', direction='LONG', grade='LOW', score=50, cross=False, entry=True):
    return {
        'state': state, 'directional_bias': direction,
        'long_score': score if direction=='LONG' else 0,
        'short_score': score if direction=='SHORT' else 0,
        'signal_quality': {
            'grade': grade,
            'cross_market_long': cross if direction=='LONG' else False,
            'cross_market_short': cross if direction=='SHORT' else False,
        },
        'entry_decision': {'valid': True} if entry else None,
    }

def counts():
    return {'active':0,'waiting_entry':0}

def test_learning_accepts_watch_low_quality_candidate_while_strict_rejects():
    s=sig()
    strict_ok,_=_policy(s,counts())
    learning_ok,reason=_learning_policy(s,counts())
    assert strict_ok is False
    assert learning_ok is True
    assert reason == 'LEARNING_POLICY_OK'

def test_learning_rejects_score_below_floor():
    ok,reason=_learning_policy(sig(score=44),counts())
    assert ok is False
    assert reason == 'LEARNING_SCORE_TOO_LOW'

def test_strict_policy_stays_strict():
    ok,reason=_policy(sig(state='SETUP_FORMING',grade='HIGH',score=75,cross=False),counts())
    assert ok is False
    assert 'CROSS_MARKET' in reason
