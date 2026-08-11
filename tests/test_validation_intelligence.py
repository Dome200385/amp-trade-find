from app.services.validation_intelligence import _score_bucket, _confidence_bucket, _stats

def test_buckets():
    assert _score_bucket(88) == "85-89"
    assert _confidence_bucket(84) == "80-89"
    assert _confidence_bucket(None) == "LEGACY"

def test_stats_empty():
    s = _stats([])
    assert s["captured"] == 0
    assert s["resolved"] == 0
    assert s["expectancy_r"] is None
