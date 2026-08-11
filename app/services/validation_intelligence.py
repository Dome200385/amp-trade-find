from collections import defaultdict
from app.services.unified_validation import (
    validation_rows, normalized_outcome, r_value, RESOLVED_OUTCOMES
)

def _score_bucket(score):
    if score is None: return "UNKNOWN"
    score = int(score)
    if score >= 90: return "90+"
    if score >= 85: return "85-89"
    if score >= 80: return "80-84"
    if score >= 75: return "75-79"
    if score >= 70: return "70-74"
    return "<70"

def _confidence_bucket(value):
    if value is None: return "LEGACY"
    v = float(value)
    if v >= 90: return "90+"
    if v >= 80: return "80-89"
    if v >= 70: return "70-79"
    if v >= 60: return "60-69"
    return "<60"

def _stats(rows):
    resolved = [r for r in rows if normalized_outcome(r.get("outcome")) in RESOLVED_OUTCOMES]
    rvals = [r_value(r) for r in resolved]
    rvals = [x for x in rvals if x is not None]
    wins = [x for x in rvals if x > 0]
    losses = [x for x in rvals if x < 0]
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    confidences = []
    for r in rows:
        if r.get("confidence_pct") is not None:
            try: confidences.append(float(r["confidence_pct"]))
            except Exception: pass

    outcomes = [normalized_outcome(r.get("outcome")) for r in resolved]
    n = len(resolved)
    return {
        "captured": len(rows),
        "resolved": n,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": round(len(wins)/n*100,2) if n else None,
        "profit_factor": round(gross_win/gross_loss,3) if gross_loss else (999.0 if gross_win else None),
        "expectancy_r": round(sum(rvals)/len(rvals),4) if rvals else None,
        "avg_confidence": round(sum(confidences)/len(confidences),2) if confidences else None,
        "tp1_rate_pct": round(outcomes.count("TP1")/n*100,2) if n else None,
        "tp2_rate_pct": round(outcomes.count("TP2")/n*100,2) if n else None,
        "stop_rate_pct": round(outcomes.count("STOPPED")/n*100,2) if n else None,
    }

def _rank_score(stats):
    n = stats["resolved"]
    if not n: return -999
    exp = stats["expectancy_r"] or 0
    pf = min(stats["profit_factor"] or 0, 3)
    win = (stats["win_rate_pct"] or 0)/100
    sample_weight = min(n/20,1)
    return round((exp*45 + pf*15 + win*25)*sample_weight,3)

def build_intelligence():
    rows = validation_rows()

    dims = {
        "direction": defaultdict(list),
        "setup_grade": defaultdict(list),
        "quality": defaultdict(list),
        "confidence": defaultdict(list),
        "score": defaultdict(list),
    }
    for r in rows:
        dims["direction"][r.get("direction") or "UNKNOWN"].append(r)
        dims["setup_grade"][r.get("setup_grade") or "LEGACY"].append(r)
        dims["quality"][r.get("quality_grade") or "UNKNOWN"].append(r)
        dims["confidence"][_confidence_bucket(r.get("confidence_pct"))].append(r)
        dims["score"][_score_bucket(r.get("score"))].append(r)

    out = {
        "overall": _stats(rows),
        "dimensions": {},
        "leaderboard": [],
    }
    for name, groups in dims.items():
        out["dimensions"][name] = {k:_stats(v) for k,v in sorted(groups.items())}

    combos = defaultdict(list)
    for r in rows:
        key = (
            r.get("direction") or "UNKNOWN",
            r.get("setup_grade") or "LEGACY",
            _confidence_bucket(r.get("confidence_pct")),
        )
        combos[key].append(r)

    board = []
    for (direction,grade,confidence),group in combos.items():
        st = _stats(group)
        if st["resolved"] == 0:
            continue
        board.append({
            "direction":direction,
            "setup_grade":grade,
            "confidence_bucket":confidence,
            **st,
            "rank_score":_rank_score(st),
        })
    board.sort(key=lambda x:(x["rank_score"],x["resolved"]),reverse=True)
    out["leaderboard"] = board[:12]
    return out
