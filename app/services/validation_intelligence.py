import sqlite3
from collections import defaultdict
from app.config import settings

RESOLVED_OUTCOMES = {"TP1", "TP2", "STOPPED", "EXPIRED"}

def _connect():
    db = sqlite3.connect(settings.database_path)
    db.row_factory = sqlite3.Row
    return db

def _columns(db, table):
    return {r["name"] for r in db.execute(f"PRAGMA table_info({table})").fetchall()}

def _pick(cols, *names):
    for n in names:
        if n in cols:
            return n
    return None

def _select_expr(cols, alias, *names, default="NULL"):
    col = _pick(cols, *names)
    return f"{col} AS {alias}" if col else f"{default} AS {alias}"

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

def _normalized_outcome(row):
    raw = str(row.get("outcome") or row.get("status") or "").upper()
    if raw in ("STOP", "SL", "LOSS"): return "STOPPED"
    if raw in ("WIN", "TARGET1"): return "TP1"
    if raw == "TARGET2": return "TP2"
    return raw

def _r_value(row):
    val = row.get("close_r")
    if val is not None:
        try: return float(val)
        except: pass
    outcome = _normalized_outcome(row)
    rr = row.get("rr")
    try: rr = float(rr) if rr is not None else 1.5
    except: rr = 1.5
    if outcome == "TP2": return rr
    if outcome == "TP1": return rr
    if outcome == "STOPPED": return -1.0
    if outcome == "EXPIRED": return 0.0
    return None

def _resolved(rows):
    return [r for r in rows if _normalized_outcome(r) in RESOLVED_OUTCOMES]

def _stats(rows):
    resolved = _resolved(rows)
    rvals = [_r_value(r) for r in resolved]
    rvals = [x for x in rvals if x is not None]
    wins = [x for x in rvals if x > 0]
    losses = [x for x in rvals if x < 0]
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    confidences = []
    for r in rows:
        if r.get("confidence_pct") is not None:
            try: confidences.append(float(r["confidence_pct"]))
            except: pass
    outcomes = [_normalized_outcome(r) for r in resolved]
    n = len(resolved)
    return {
        "captured": len(rows),
        "resolved": n,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": round(len(wins)/n*100,2) if n else None,
        "profit_factor": round(gross_win/gross_loss,3) if gross_loss else (None if not gross_win else 999.0),
        "expectancy_r": round(sum(rvals)/len(rvals),4) if rvals else None,
        "avg_confidence": round(sum(confidences)/len(confidences),2) if confidences else None,
        "tp1_rate_pct": round(outcomes.count("TP1")/n*100,2) if n else None,
        "tp2_rate_pct": round(outcomes.count("TP2")/n*100,2) if n else None,
        "stop_rate_pct": round(outcomes.count("STOPPED")/n*100,2) if n else None,
    }

def _load_rows():
    with _connect() as db:
        cols = _columns(db, "validation_setups")
        if not cols:
            return []
        fields = [
            _select_expr(cols, "direction", "direction", default="'UNKNOWN'"),
            _select_expr(cols, "quality_grade", "quality_grade", "quality", default="'UNKNOWN'"),
            _select_expr(cols, "setup_grade", "setup_grade", "grade"),
            _select_expr(cols, "confidence_pct", "confidence_pct", "confidence"),
            _select_expr(cols, "score", "score"),
            _select_expr(cols, "outcome", "outcome"),
            _select_expr(cols, "status", "status"),
            _select_expr(cols, "close_r", "close_r", "result_r", "realized_r"),
            _select_expr(cols, "rr", "rr", "risk_reward", "target_rr"),
            _select_expr(cols, "capture_hour_utc", "capture_hour_utc"),
            _select_expr(cols, "created_at", "created_at", "captured_at", "created_at_utc"),
        ]
        order_col = _pick(cols, "created_at", "captured_at", "created_at_utc", "id")
        sql = "SELECT " + ", ".join(fields) + " FROM validation_setups"
        if order_col:
            sql += f" ORDER BY {order_col} DESC"
        return [dict(r) for r in db.execute(sql).fetchall()]

def _rank_score(stats):
    n = stats["resolved"]
    if not n: return -999
    exp = stats["expectancy_r"] or 0
    pf = stats["profit_factor"]
    pf = min(pf if pf is not None else 0, 3)
    win = (stats["win_rate_pct"] or 0)/100
    sample_weight = min(n/20, 1)
    return round((exp*45 + pf*15 + win*25) * sample_weight, 3)

def build_intelligence():
    rows = _load_rows()
    dimensions = {
        "direction": defaultdict(list),
        "setup_grade": defaultdict(list),
        "quality": defaultdict(list),
        "confidence": defaultdict(list),
        "score": defaultdict(list),
    }
    for r in rows:
        dimensions["direction"][r.get("direction") or "UNKNOWN"].append(r)
        dimensions["setup_grade"][r.get("setup_grade") or "LEGACY"].append(r)
        dimensions["quality"][r.get("quality_grade") or "UNKNOWN"].append(r)
        dimensions["confidence"][_confidence_bucket(r.get("confidence_pct"))].append(r)
        dimensions["score"][_score_bucket(r.get("score"))].append(r)

    result = {
        "overall": _stats(rows),
        "dimensions": {},
        "leaderboard": [],
        "notes": {
            "legacy_note": "Older setups without confidence/grade are included as LEGACY.",
            "sample_warning": "Use resolved sample count together with win rate, PF and expectancy."
        }
    }
    for dim, groups in dimensions.items():
        result["dimensions"][dim] = {k:_stats(v) for k,v in sorted(groups.items())}

    combos = defaultdict(list)
    for r in rows:
        key = (
            r.get("direction") or "UNKNOWN",
            r.get("setup_grade") or "LEGACY",
            _confidence_bucket(r.get("confidence_pct")),
        )
        combos[key].append(r)

    board = []
    for (direction, grade, confidence), group in combos.items():
        st = _stats(group)
        if st["resolved"] == 0:
            continue
        board.append({
            "direction": direction,
            "setup_grade": grade,
            "confidence_bucket": confidence,
            **st,
            "rank_score": _rank_score(st),
        })
    board.sort(key=lambda x:(x["rank_score"], x["resolved"]), reverse=True)
    result["leaderboard"] = board[:12]
    return result
