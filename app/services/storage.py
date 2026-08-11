import json
import sqlite3
from datetime import datetime, timezone, timedelta
from app.config import settings

def _connect():
    db = sqlite3.connect(settings.database_path)
    db.row_factory = sqlite3.Row
    return db

def _columns(db, table):
    return {r["name"] for r in db.execute(f"PRAGMA table_info({table})").fetchall()}

def init_db():
    with _connect() as db:
        db.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            signal_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            symbol TEXT NOT NULL,
            price REAL NOT NULL,
            state TEXT NOT NULL,
            candidate TEXT NOT NULL,
            long_score INTEGER NOT NULL,
            short_score INTEGER NOT NULL,
            market_bias TEXT NOT NULL,
            setup TEXT NOT NULL,
            snapshot_json TEXT NOT NULL,
            signal_json TEXT NOT NULL,
            outcome TEXT,
            outcome_at TEXT
        )
        """)
        cols = _columns(db, "signals")
        migrations = {
            "entry": "REAL",
            "stop": "REAL",
            "target1": "REAL",
            "target2": "REAL",
            "expires_at": "TEXT",
            "max_favorable_price": "REAL",
            "max_adverse_price": "REAL",
            "strategy_version": "TEXT",
            "gate_reason": "TEXT"
        }
        for name, typ in migrations.items():
            if name not in cols:
                db.execute(f"ALTER TABLE signals ADD COLUMN {name} {typ}")
        db.commit()

def save_signal(snapshot: dict, signal: dict):
    now = datetime.now(timezone.utc)
    plan = signal.get("trade_plan")
    expires_at = None
    if plan:
        expires_at = (now + timedelta(minutes=int(plan.get("validity_minutes", 15)))).isoformat()

    with _connect() as db:
        db.execute("""
        INSERT OR REPLACE INTO signals (
            signal_id, created_at, symbol, price, state, candidate,
            long_score, short_score, market_bias, setup,
            snapshot_json, signal_json, outcome, outcome_at,
            entry, stop, target1, target2, expires_at,
            max_favorable_price, max_adverse_price, strategy_version, gate_reason
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            signal["signal_id"], now.isoformat(), signal["symbol"], signal["price"],
            signal["state"], signal["candidate_opportunity"],
            signal["long_score"], signal["short_score"], signal["market_bias"], signal["setup"],
            json.dumps(snapshot, separators=(",", ":")),
            json.dumps(signal, separators=(",", ":")),
            "ACTIVE" if plan else None, None,
            plan.get("entry") if plan else None,
            plan.get("stop") if plan else None,
            plan.get("target1") if plan else None,
            plan.get("target2") if plan else None,
            expires_at,
            signal["price"] if plan else None,
            signal["price"] if plan else None,
            settings.strategy_version,
            signal.get("gate_reason"),
        ))
        db.commit()

def active_signals():
    with _connect() as db:
        return [dict(r) for r in db.execute("""
            SELECT * FROM signals
            WHERE outcome='ACTIVE' AND candidate IN ('LONG','SHORT')
            ORDER BY created_at ASC
        """).fetchall()]

def update_outcome(signal_id: str, outcome: str, price: float):
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as db:
        row = db.execute("SELECT * FROM signals WHERE signal_id=?", (signal_id,)).fetchone()
        if not row:
            return

        mf = row["max_favorable_price"]
        ma = row["max_adverse_price"]
        candidate = row["candidate"]

        if candidate == "LONG":
            mf = max(mf or price, price)
            ma = min(ma or price, price)
        else:
            mf = min(mf or price, price)
            ma = max(ma or price, price)

        db.execute("""
            UPDATE signals
            SET outcome=?, outcome_at=?, max_favorable_price=?, max_adverse_price=?
            WHERE signal_id=?
        """, (outcome, now if outcome != "ACTIVE" else row["outcome_at"], mf, ma, signal_id))
        db.commit()

def recent_signals(limit: int = 50):
    limit = max(1, min(int(limit), 500))
    with _connect() as db:
        rows = db.execute("""
        SELECT signal_id, created_at, symbol, price, state, candidate,
               long_score, short_score, market_bias, setup, outcome, outcome_at,
               entry, stop, target1, target2, expires_at,
               max_favorable_price, max_adverse_price, strategy_version, gate_reason
        FROM signals
        ORDER BY created_at DESC
        LIMIT ?
        """, (limit,)).fetchall()
    return [dict(r) for r in rows]

def performance_stats():
    with _connect() as db:
        rows = db.execute("""
            SELECT outcome, COUNT(*) AS n
            FROM signals
            WHERE candidate IN ('LONG','SHORT') AND outcome IS NOT NULL
            GROUP BY outcome
        """).fetchall()
        by_direction = db.execute("""
            SELECT candidate, outcome, COUNT(*) AS n
            FROM signals
            WHERE candidate IN ('LONG','SHORT') AND outcome IS NOT NULL
            GROUP BY candidate, outcome
        """).fetchall()

    counts = {r["outcome"]: r["n"] for r in rows}
    resolved = sum(v for k, v in counts.items() if k in ("TP1", "TP2", "STOPPED"))
    wins = counts.get("TP1", 0) + counts.get("TP2", 0)
    win_rate = (wins / resolved * 100.0) if resolved else None

    return {
        "counts": counts,
        "resolved_trades": resolved,
        "wins": wins,
        "losses": counts.get("STOPPED", 0),
        "expired": counts.get("EXPIRED", 0),
        "active": counts.get("ACTIVE", 0),
        "win_rate_pct": round(win_rate, 2) if win_rate is not None else None,
        "by_direction": [dict(r) for r in by_direction],
        "minimum_samples_for_validation": settings.min_validated_samples,
        "validation_sample_gate_passed": resolved >= settings.min_validated_samples,
    }


def get_signal_detail(signal_id: str):
    with _connect() as db:
        row = db.execute("""
            SELECT signal_id, created_at, symbol, price, state, candidate,
                   long_score, short_score, market_bias, setup, outcome, outcome_at,
                   entry, stop, target1, target2, expires_at,
                   max_favorable_price, max_adverse_price,
                   strategy_version, gate_reason, signal_json, snapshot_json
            FROM signals
            WHERE signal_id=?
        """, (signal_id,)).fetchone()
    if not row:
        return None
    out = dict(row)
    try:
        out["signal"] = json.loads(out.pop("signal_json"))
    except Exception:
        out["signal"] = {}
    try:
        out["snapshot"] = json.loads(out.pop("snapshot_json"))
    except Exception:
        out["snapshot"] = {}
    return out
