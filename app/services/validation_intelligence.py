import sqlite3
from collections import defaultdict
from app.config import settings

def _connect():
    db = sqlite3.connect(settings.database_path)
    db.row_factory = sqlite3.Row
    return db

def _score_bucket(score):
    score = int(score or 0)
    if score >= 90: return "90+"
    if score >= 85: return "85-89"
    if score >= 80: return "80-84"
    if score >= 75: return "75-79"
    if score >= 70: return "70-74"
    return "65-69"

def _confidence_bucket(value):
    if value is None:
        return "LEGACY"
    v = float(value)
    if v >= 90: return "90+"
    if v >= 80: return "80-89"
    if v >= 70: return "70-79"
    if v >= 60: return "60-69"
    return "<60"

def _resolved(rows):
    return [r for r in rows if r["outcome"] in ("TP1","TP2","STOPPED","EXPIRED")]

def _stats(rows):
    resolved = _resolved(rows)
    if not rows:
        return {
            "captured":0,"resolved":0,"wins":0,"losses":0,"win_rate_pct":None,
            "profit_factor":None,"expectancy_r":None,"avg_confidence":None,
            "tp1_rate_pct":None,"tp2_rate_pct":None,"stop_rate_pct":None,
        }

    wins = [r for r in resolved if float(r["close_r"] or 0) > 0]
    losses = [r for r in resolved if float(r["close_r"] or 0) < 0]

    gross_win = sum(max(float(r["close_r"] or 0),0) for r in resolved)
    gross_loss = abs(sum(min(float(r["close_r"] or 0),0) for r in resolved))
    pf = gross_win/gross_loss if gross_loss else None
    expectancy = (
        sum(float(r["close_r"] or 0) for r in resolved)/len(resolved)
        if resolved else None
    )

    confidences = [float(r["confidence_pct"]) for r in rows if r["confidence_pct"] is not None]
    tp1 = sum(1 for r in resolved if r["outcome"]=="TP1")
    tp2 = sum(1 for r in resolved if r["outcome"]=="TP2")
    stopped = sum(1 for r in resolved if r["outcome"]=="STOPPED")

    return {
        "captured":len(rows),
        "resolved":len(resolved),
        "wins":len(wins),
        "losses":len(losses),
        "win_rate_pct":round(len(wins)/len(resolved)*100,2) if resolved else None,
        "profit_factor":round(pf,3) if pf is not None else None,
        "expectancy_r":round(expectancy,4) if expectancy is not None else None,
        "avg_confidence":round(sum(confidences)/len(confidences),2) if confidences else None,
        "tp1_rate_pct":round(tp1/len(resolved)*100,2) if resolved else None,
        "tp2_rate_pct":round(tp2/len(resolved)*100,2) if resolved else None,
        "stop_rate_pct":round(stopped/len(resolved)*100,2) if resolved else None,
    }

def _rank_score(stats):
    resolved = stats["resolved"]
    if resolved == 0:
        return -999
    exp = stats["expectancy_r"] or 0
    pf = stats["profit_factor"] if stats["profit_factor"] is not None else 3.0
    win = (stats["win_rate_pct"] or 0)/100
    sample_weight = min(resolved/20,1.0)
    return round((exp*45 + min(pf,3)*15 + win*25) * sample_weight, 3)

def build_intelligence():
    with _connect() as db:
        rows = [dict(r) for r in db.execute("""
            SELECT direction, quality_grade, setup_grade, confidence_pct, score,
                   outcome, close_r, entry_reached, capture_hour_utc,
                   primary_source, live_cvd_direction
            FROM validation_setups
            ORDER BY created_at DESC
        """).fetchall()]

    dimensions = {
        "direction": defaultdict(list),
        "setup_grade": defaultdict(list),
        "quality": defaultdict(list),
        "confidence": defaultdict(list),
        "score": defaultdict(list),
        "hour_utc": defaultdict(list),
    }

    for r in rows:
        dimensions["direction"][r["direction"] or "UNKNOWN"].append(r)
        dimensions["setup_grade"][r.get("setup_grade") or "LEGACY"].append(r)
        dimensions["quality"][r["quality_grade"] or "UNKNOWN"].append(r)
        dimensions["confidence"][_confidence_bucket(r.get("confidence_pct"))].append(r)
        dimensions["score"][_score_bucket(r.get("score"))].append(r)
        dimensions["hour_utc"][str(r.get("capture_hour_utc"))].append(r)

    result = {
        "overall": _stats(rows),
        "dimensions": {},
        "leaderboard": [],
        "notes": {
            "ranking_warning": "Small sample groups can rank highly by chance. Use resolved sample count with every metric.",
            "legacy_note": "Setups captured before V9.2 have no confidence/grade and appear as LEGACY."
        }
    }

    for dim, groups in dimensions.items():
        result["dimensions"][dim] = {
            key:_stats(group) for key,group in sorted(groups.items())
        }

    # Combination leaderboard: direction + grade + confidence bucket.
    combos = defaultdict(list)
    for r in rows:
        key = (
            r["direction"] or "UNKNOWN",
            r.get("setup_grade") or "LEGACY",
            _confidence_bucket(r.get("confidence_pct"))
        )
        combos[key].append(r)

    board = []
    for (direction, grade, confidence_bucket), group in combos.items():
        stats = _stats(group)
        board.append({
            "direction": direction,
            "setup_grade": grade,
            "confidence_bucket": confidence_bucket,
            **stats,
            "rank_score": _rank_score(stats),
        })

    board.sort(key=lambda x: (x["rank_score"], x["resolved"]), reverse=True)
    result["leaderboard"] = board[:12]
    return result
