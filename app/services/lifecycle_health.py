import sqlite3
from app.config import settings

RESOLVED = {"TP1","TP2","STOPPED","EXPIRED"}

def _connect():
    db = sqlite3.connect(settings.database_path)
    db.row_factory = sqlite3.Row
    return db

def _columns(db):
    return {r["name"] for r in db.execute("PRAGMA table_info(validation_setups)").fetchall()}

def lifecycle_health():
    with _connect() as db:
        cols = _columns(db)
        if not cols:
            return {
                "counts":{}, "waiting_entry":0, "active":0, "resolved":0,
                "missed_entry":0, "open_total":0, "healthy":False,
                "reason":"VALIDATION_TABLE_MISSING"
            }

        outcome_col = "outcome" if "outcome" in cols else ("status" if "status" in cols else None)
        if not outcome_col:
            return {
                "counts":{}, "waiting_entry":0, "active":0, "resolved":0,
                "missed_entry":0, "open_total":0, "healthy":False,
                "reason":"OUTCOME_COLUMN_MISSING"
            }

        rows = [dict(r) for r in db.execute(
            f"SELECT {outcome_col} AS outcome, COUNT(*) AS n FROM validation_setups GROUP BY {outcome_col}"
        ).fetchall()]

    counts = {}
    for r in rows:
        key = str(r["outcome"] or "UNKNOWN").upper()
        counts[key] = int(r["n"] or 0)

    waiting = counts.get("WAITING_ENTRY",0)
    active = counts.get("ACTIVE",0)
    resolved = sum(counts.get(x,0) for x in RESOLVED)
    missed = counts.get("MISSED_ENTRY",0)

    return {
        "counts": counts,
        "waiting_entry": waiting,
        "active": active,
        "resolved": resolved,
        "missed_entry": missed,
        "open_total": waiting + active,
        "healthy": True,
        "reason": None,
    }
