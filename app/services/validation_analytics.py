import sqlite3
from collections import defaultdict
from app.config import settings

def _connect():
    db = sqlite3.connect(settings.database_path)
    db.row_factory = sqlite3.Row
    return db

def _score_bucket(score):
    if score >= 90: return "90+"
    if score >= 85: return "85-89"
    if score >= 80: return "80-84"
    if score >= 75: return "75-79"
    if score >= 70: return "70-74"
    return "65-69"

def _confidence_bucket(value):
    if value is None: return "LEGACY"
    v = float(value)
    if v >= 85: return "85+"
    if v >= 75: return "75-84"
    if v >= 65: return "65-74"
    return "<65"

def _stats(rows):
    resolved = [r for r in rows if r["outcome"] in ("TP1","TP2","STOPPED","EXPIRED")]
    entered = [r for r in rows if r["entry_reached"]]
    wins = [r for r in resolved if (r["close_r"] or 0) > 0]
    losses = [r for r in resolved if (r["close_r"] or 0) < 0]
    pos = sum(max(float(r["close_r"] or 0),0) for r in resolved)
    neg = abs(sum(min(float(r["close_r"] or 0),0) for r in resolved))
    expectancy = sum(float(r["close_r"] or 0) for r in resolved)/len(resolved) if resolved else None
    pf = pos/neg if neg else None

    tp1 = sum(1 for r in resolved if r.get("tp1_hit") or r["outcome"] in ("TP1","TP2"))
    tp2 = sum(1 for r in resolved if r.get("tp2_hit") or r["outcome"] == "TP2")
    stopped = sum(1 for r in resolved if r["outcome"] == "STOPPED")
    expired = sum(1 for r in resolved if r["outcome"] == "EXPIRED")

    return {
        "captured": len(rows),
        "entered": len(entered),
        "resolved": len(resolved),
        "wins": len(wins),
        "losses": len(losses),
        "missed_entry": sum(1 for r in rows if r["outcome"]=="MISSED_ENTRY"),
        "capture_rate_pct": None,
        "win_rate_pct": round(len(wins)/len(resolved)*100,2) if resolved else None,
        "profit_factor": round(pf,3) if pf is not None else None,
        "expectancy_r": round(expectancy,4) if expectancy is not None else None,
        "avg_mfe_r": round(sum(float(r["mfe_r"] or 0) for r in entered)/len(entered),4) if entered else None,
        "avg_mae_r": round(sum(float(r["mae_r"] or 0) for r in entered)/len(entered),4) if entered else None,
        "tp1": tp1,
        "tp2": tp2,
        "stopped": stopped,
        "expired": expired,
        "tp1_rate_pct": round(tp1/len(resolved)*100,2) if resolved else None,
        "tp2_rate_pct": round(tp2/len(resolved)*100,2) if resolved else None,
        "stop_rate_pct": round(stopped/len(resolved)*100,2) if resolved else None,
    }

def validation_report():
    with _connect() as db:
        rows = [dict(r) for r in db.execute("""
            SELECT direction, quality_grade, setup_grade, confidence_pct, score,
                   entry_reached, outcome, close_r, mfe_r, mae_r,
                   capture_hour_utc, live_cvd_direction, primary_source,
                   tp1_hit, tp2_hit, post_tp1_stop
            FROM validation_setups
        """).fetchall()]

    overall = _stats(rows)

    groups = {
        "by_direction": defaultdict(list),
        "by_quality": defaultdict(list),
        "by_setup_grade": defaultdict(list),
        "by_score_bucket": defaultdict(list),
        "by_confidence_bucket": defaultdict(list),
        "by_hour_utc": defaultdict(list),
    }
    for r in rows:
        groups["by_direction"][r["direction"]].append(r)
        groups["by_quality"][r["quality_grade"]].append(r)
        groups["by_setup_grade"][r.get("setup_grade") or "LEGACY"].append(r)
        groups["by_score_bucket"][_score_bucket(int(r["score"]))].append(r)
        groups["by_confidence_bucket"][_confidence_bucket(r.get("confidence_pct"))].append(r)
        groups["by_hour_utc"][str(r["capture_hour_utc"])].append(r)

    result = {"overall": overall}
    for key, grouped in groups.items():
        result[key] = {name:_stats(sub) for name,sub in sorted(grouped.items())}

    resolved = overall["resolved"]
    pf = overall["profit_factor"] or 0
    exp = overall["expectancy_r"] or 0
    result["validation_gate"] = {
        "minimum_resolved_samples": settings.validation_min_resolved_samples,
        "minimum_profit_factor": settings.validation_min_profit_factor,
        "minimum_expectancy_r": settings.validation_min_expectancy_r,
        "sample_gate_passed": resolved >= settings.validation_min_resolved_samples,
        "profit_factor_gate_passed": resolved >= settings.validation_min_resolved_samples and pf >= settings.validation_min_profit_factor,
        "expectancy_gate_passed": resolved >= settings.validation_min_resolved_samples and exp >= settings.validation_min_expectancy_r,
        "all_gates_passed": (
            resolved >= settings.validation_min_resolved_samples
            and pf >= settings.validation_min_profit_factor
            and exp >= settings.validation_min_expectancy_r
        )
    }
    return result
