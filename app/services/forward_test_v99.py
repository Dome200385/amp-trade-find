import sqlite3
from app.config import settings

STRATEGY = "FIND-V9.9-1"

def _connect():
    db = sqlite3.connect(settings.database_path)
    db.row_factory = sqlite3.Row
    return db

def v99_forward_status():
    try:
        with _connect() as db:
            rows = [dict(r) for r in db.execute(
                """
                SELECT outcome, close_r, rr1
                FROM validation_setups
                WHERE strategy_version=?
                  AND outcome IN ('TP1','TP2','STOPPED','EXPIRED')
                """,
                (STRATEGY,),
            ).fetchall()]
    except sqlite3.Error:
        rows = []

    vals = []
    for r in rows:
        if r.get("close_r") is not None:
            try:
                vals.append(float(r["close_r"]))
                continue
            except Exception:
                pass
        outcome = str(r.get("outcome") or "").upper()
        rr = float(r.get("rr1") or 1.5)
        vals.append(rr if outcome in ("TP1", "TP2") else (-1.0 if outcome == "STOPPED" else 0.0))

    wins = [x for x in vals if x > 0]
    losses = [x for x in vals if x < 0]
    pos = sum(wins)
    neg = abs(sum(losses))
    n = len(vals)
    target = settings.v99_forward_target_resolved
    return {
        "strategy": STRATEGY,
        "status": "READY" if n >= target else "COLLECTING",
        "resolved": n,
        "target": target,
        "win_rate_pct": round(len(wins) / n * 100, 1) if n else None,
        "profit_factor": round(pos / neg, 2) if neg else (999.0 if pos else None),
        "expectancy_r": round(sum(vals) / n, 3) if n else None,
    }
