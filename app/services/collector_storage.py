import sqlite3
from datetime import datetime, timezone
from app.config import settings

def _connect():
    db=sqlite3.connect(settings.database_path); db.row_factory=sqlite3.Row; return db

def init_collector_db():
    with _connect() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS collector_runs(
          id INTEGER PRIMARY KEY AUTOINCREMENT, run_at TEXT NOT NULL,
          state TEXT,direction TEXT,quality_grade TEXT,long_score INTEGER,short_score INTEGER,
          captured INTEGER NOT NULL DEFAULT 0,capture_reason TEXT,primary_source TEXT,
          available_venues INTEGER,active_validation_setups INTEGER,error TEXT)""")
        db.execute("CREATE INDEX IF NOT EXISTS idx_collector_runs_at ON collector_runs(run_at)")
        db.commit()

def record_run(**x):
    with _connect() as db:
        db.execute("""INSERT INTO collector_runs(
          run_at,state,direction,quality_grade,long_score,short_score,captured,capture_reason,
          primary_source,available_venues,active_validation_setups,error)
          VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",(
          datetime.now(timezone.utc).isoformat(),x.get("state"),x.get("direction"),x.get("quality_grade"),
          int(x.get("long_score") or 0),int(x.get("short_score") or 0),1 if x.get("captured") else 0,
          x.get("capture_reason"),x.get("primary_source"),int(x.get("available_venues") or 0),
          int(x.get("active_validation_setups") or 0),x.get("error")))
        db.commit()

def collector_stats(hours=24):
    hours=max(1,min(int(hours),720))
    with _connect() as db:
        rows=[dict(r) for r in db.execute(
          "SELECT * FROM collector_runs WHERE run_at >= datetime('now', ?) ORDER BY run_at DESC",
          (f"-{hours} hours",)).fetchall()]
    states={}; reasons={}; quality={}
    for r in rows:
        sk=r["state"] or "UNKNOWN"; rk=r["capture_reason"] or "UNKNOWN"; qk=r["quality_grade"] or "UNKNOWN"
        states[sk]=states.get(sk,0)+1; reasons[rk]=reasons.get(rk,0)+1; quality[qk]=quality.get(qk,0)+1
    captures=sum(int(r["captured"] or 0) for r in rows)
    return {"window_hours":hours,"runs":len(rows),"captures":captures,
      "capture_rate_pct":round(captures/len(rows)*100,3) if rows else None,
      "states":states,"reasons":reasons,"quality":quality,"last_run":rows[0] if rows else None}
