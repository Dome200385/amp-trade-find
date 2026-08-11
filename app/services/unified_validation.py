import sqlite3
from app.config import settings

RESOLVED_OUTCOMES = {"TP1","TP2","STOPPED","EXPIRED"}

def _connect():
    db = sqlite3.connect(settings.database_path)
    db.row_factory = sqlite3.Row
    return db

def _columns(db):
    return {r["name"] for r in db.execute("PRAGMA table_info(validation_setups)").fetchall()}

def _pick(cols, *names):
    for name in names:
        if name in cols:
            return name
    return None

def validation_rows():
    with _connect() as db:
        cols = _columns(db)
        if not cols:
            return []

        outcome_col = _pick(cols, "outcome", "status")
        direction_col = _pick(cols, "direction")
        score_col = _pick(cols, "score")
        quality_col = _pick(cols, "quality_grade", "quality")
        grade_col = _pick(cols, "setup_grade", "grade")
        confidence_col = _pick(cols, "confidence_pct", "confidence")
        close_r_col = _pick(cols, "close_r", "result_r", "realized_r")
        rr_col = _pick(cols, "rr1", "rr", "risk_reward", "target_rr")
        created_col = _pick(cols, "created_at", "captured_at", "created_at_utc")

        def expr(col, alias, default="NULL"):
            return f"{col} AS {alias}" if col else f"{default} AS {alias}"

        fields = [
            expr(outcome_col, "outcome", "''"),
            expr(direction_col, "direction", "'UNKNOWN'"),
            expr(score_col, "score"),
            expr(quality_col, "quality_grade", "'UNKNOWN'"),
            expr(grade_col, "setup_grade"),
            expr(confidence_col, "confidence_pct"),
            expr(close_r_col, "close_r"),
            expr(rr_col, "rr1"),
            expr(created_col, "created_at"),
        ]
        sql = "SELECT " + ", ".join(fields) + " FROM validation_setups"
        if created_col:
            sql += f" ORDER BY {created_col} DESC"
        return [dict(r) for r in db.execute(sql).fetchall()]

def normalized_outcome(value):
    raw = str(value or "").upper()
    aliases = {
        "STOP":"STOPPED",
        "SL":"STOPPED",
        "LOSS":"STOPPED",
        "WIN":"TP1",
        "TARGET1":"TP1",
        "TARGET2":"TP2",
    }
    return aliases.get(raw, raw)

def validation_counts_unified():
    rows = validation_rows()
    counts = {}
    for r in rows:
        outcome = normalized_outcome(r.get("outcome"))
        counts[outcome] = counts.get(outcome, 0) + 1

    resolved = sum(counts.get(x,0) for x in RESOLVED_OUTCOMES)
    return {
        "captured": len(rows),
        "waiting_entry": counts.get("WAITING_ENTRY",0),
        "active": counts.get("ACTIVE",0),
        "resolved": resolved,
        "missed_entry": counts.get("MISSED_ENTRY",0),
        "counts": counts,
        "rows": rows,
    }

def r_value(row):
    if row.get("close_r") is not None:
        try:
            return float(row["close_r"])
        except Exception:
            pass

    outcome = normalized_outcome(row.get("outcome"))
    try:
        rr = float(row.get("rr1") or 1.5)
    except Exception:
        rr = 1.5

    if outcome in ("TP1","TP2"):
        return rr
    if outcome == "STOPPED":
        return -1.0
    if outcome == "EXPIRED":
        return 0.0
    return None
