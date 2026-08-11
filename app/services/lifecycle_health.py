import sqlite3
from app.config import settings

def _connect():
    db=sqlite3.connect(settings.database_path)
    db.row_factory=sqlite3.Row
    return db

def lifecycle_health():
    with _connect() as db:
        rows=[dict(r) for r in db.execute("""
          SELECT outcome, COUNT(*) AS n
          FROM validation_setups
          GROUP BY outcome
        """).fetchall()]
    counts={r["outcome"]:r["n"] for r in rows}
    waiting=int(counts.get("WAITING_ENTRY",0))
    active=int(counts.get("ACTIVE",0))
    resolved=sum(int(counts.get(x,0)) for x in ("TP1","TP2","STOPPED","EXPIRED"))
    missed=int(counts.get("MISSED_ENTRY",0))
    return {
        "counts":counts,
        "waiting_entry":waiting,
        "active":active,
        "resolved":resolved,
        "missed_entry":missed,
        "open_total":waiting+active,
        "healthy": True,
    }
