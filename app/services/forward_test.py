import sqlite3
from app.config import settings


def _connect():
    db = sqlite3.connect(settings.database_path)
    db.row_factory = sqlite3.Row
    return db


def init_forward_test():
    from app.services.regime_prior import init_regime_prior
    frozen_at = init_regime_prior()
    with _connect() as db:
        db.execute("CREATE TABLE IF NOT EXISTS forward_test_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
        row = db.execute("SELECT value FROM forward_test_meta WHERE key='started_at'").fetchone()
        if not row:
            db.execute("INSERT INTO forward_test_meta(key,value) VALUES('started_at',?)", (frozen_at,))
        db.commit()


def forward_test_status():
    try:
        with _connect() as db:
            row = db.execute("SELECT value FROM forward_test_meta WHERE key='started_at'").fetchone()
            if not row:
                return {"readiness": "NOT_STARTED", "captured": 0, "resolved": 0, "target": settings.forward_test_target_resolved}
            start = row["value"]
            rows = [dict(r) for r in db.execute(
                "SELECT outcome,close_r FROM validation_setups WHERE created_at >= ?", (start,)
            ).fetchall()]
    except sqlite3.Error:
        return {"readiness": "UNAVAILABLE", "captured": 0, "resolved": 0, "target": settings.forward_test_target_resolved}

    resolved_rows = [r for r in rows if r.get("outcome") in ("TP1", "TP2", "STOPPED", "EXPIRED")]
    vals = [float(r.get("close_r") or 0) for r in resolved_rows]
    wins = sum(r.get("outcome") in ("TP1", "TP2") for r in resolved_rows)
    pos = sum(max(x, 0) for x in vals)
    neg = abs(sum(min(x, 0) for x in vals))
    resolved = len(resolved_rows)
    return {
        "started_at": start,
        "captured": len(rows),
        "resolved": resolved,
        "target": settings.forward_test_target_resolved,
        "readiness": "READY" if resolved >= settings.forward_test_target_resolved else "COLLECTING",
        "win_rate_pct": round(wins / resolved * 100, 1) if resolved else None,
        "profit_factor": round(pos / neg, 2) if neg else (999.0 if pos else None),
        "expectancy_r": round(sum(vals) / len(vals), 3) if vals else None,
    }
