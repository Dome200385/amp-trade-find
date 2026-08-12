import sqlite3
from datetime import datetime, timezone
from collections import Counter
from app.config import settings

def _connect():
    db = sqlite3.connect(settings.database_path)
    db.row_factory = sqlite3.Row
    return db

def init_learning_funnel_db():
    with _connect() as db:
        db.execute("""
        CREATE TABLE IF NOT EXISTS learning_funnel_runs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_at TEXT NOT NULL,
            state TEXT,
            direction TEXT,
            long_score INTEGER,
            short_score INTEGER,
            confidence_pct REAL,
            quality_grade TEXT,
            stage TEXT NOT NULL,
            strict_reason TEXT,
            learning_reason TEXT,
            captured INTEGER NOT NULL DEFAULT 0,
            capture_mode TEXT
        )
        """)
        db.execute("CREATE INDEX IF NOT EXISTS idx_funnel_run_at ON learning_funnel_runs(run_at)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_funnel_stage ON learning_funnel_runs(stage, run_at)")
        db.commit()

def classify_stage(*, strict_ok: bool, learning_ok: bool, captured: bool, capture_mode: str | None):
    if captured and capture_mode == "STRICT":
        return "STRICT_CAPTURE"
    if captured and capture_mode == "LEARNING":
        return "LEARNING_CAPTURE"
    if strict_ok:
        return "STRICT_CANDIDATE"
    if learning_ok:
        return "LEARNING_CANDIDATE"
    return "REJECTED_NOISE"

def record_funnel_run(
    *,
    signal: dict,
    strict_ok: bool,
    strict_reason: str,
    learning_ok: bool,
    learning_reason: str,
    captured: bool,
    capture_mode: str | None,
):
    q = signal.get("signal_quality") or {}
    stage = classify_stage(
        strict_ok=strict_ok,
        learning_ok=learning_ok,
        captured=captured,
        capture_mode=capture_mode,
    )
    with _connect() as db:
        db.execute("""
        INSERT INTO learning_funnel_runs(
            run_at,state,direction,long_score,short_score,confidence_pct,quality_grade,
            stage,strict_reason,learning_reason,captured,capture_mode
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            datetime.now(timezone.utc).isoformat(),
            signal.get("state"),
            signal.get("directional_bias"),
            int(signal.get("long_score") or 0),
            int(signal.get("short_score") or 0),
            signal.get("confidence_pct"),
            q.get("grade"),
            stage,
            strict_reason,
            learning_reason,
            1 if captured else 0,
            capture_mode,
        ))
        db.commit()
    return stage

def funnel_stats(hours: int = 24):
    hours = max(1, min(int(hours), 720))
    try:
        with _connect() as db:
            rows = [dict(r) for r in db.execute("""
                SELECT * FROM learning_funnel_runs
                WHERE run_at >= datetime('now', ?)
                ORDER BY run_at DESC
            """, (f"-{hours} hours",)).fetchall()]
    except sqlite3.Error:
        rows = []

    stages = Counter(r.get("stage") or "UNKNOWN" for r in rows)
    strict_reasons = Counter(r.get("strict_reason") or "NONE" for r in rows)
    learning_reasons = Counter(r.get("learning_reason") or "NONE" for r in rows)

    total = len(rows)
    candidates = (
        stages["STRICT_CANDIDATE"] + stages["LEARNING_CANDIDATE"]
        + stages["STRICT_CAPTURE"] + stages["LEARNING_CAPTURE"]
    )
    captures = stages["STRICT_CAPTURE"] + stages["LEARNING_CAPTURE"]

    return {
        "window_hours": hours,
        "scans": total,
        "candidates": candidates,
        "candidate_rate_pct": round(candidates/total*100, 2) if total else None,
        "strict_captures": stages["STRICT_CAPTURE"],
        "learning_captures": stages["LEARNING_CAPTURE"],
        "captures_total": captures,
        "capture_rate_pct": round(captures/total*100, 2) if total else None,
        "rejected_noise": stages["REJECTED_NOISE"],
        "stages": dict(stages),
        "top_strict_rejections": strict_reasons.most_common(8),
        "top_learning_rejections": learning_reasons.most_common(8),
        "last_run": rows[0] if rows else None,
    }
