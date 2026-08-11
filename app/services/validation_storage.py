import json
import sqlite3
from datetime import datetime, timezone
from app.config import settings
from app.services.setup_features import extract_setup_features

def _connect():
    db = sqlite3.connect(settings.database_path)
    db.row_factory = sqlite3.Row
    return db

def init_validation_db():
    with _connect() as db:
        db.execute("""
        CREATE TABLE IF NOT EXISTS validation_setups (
            setup_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            strategy_version TEXT NOT NULL,
            symbol TEXT NOT NULL,
            direction TEXT NOT NULL,
            state_at_capture TEXT NOT NULL,
            quality_grade TEXT NOT NULL,
            setup_grade TEXT,
            confidence_pct REAL,
            score INTEGER NOT NULL,
            long_score INTEGER NOT NULL,
            short_score INTEGER NOT NULL,
            entry_low REAL,
            entry_high REAL,
            entry_center REAL,
            stop REAL,
            target1 REAL,
            target2 REAL,
            rr1 REAL,
            rr2 REAL,
            validity_minutes INTEGER,
            entry_reached INTEGER NOT NULL DEFAULT 0,
            entry_reached_at TEXT,
            entry_fill_price REAL,
            outcome TEXT NOT NULL DEFAULT 'WAITING_ENTRY',
            outcome_at TEXT,
            mfe_price REAL,
            mae_price REAL,
            mfe_r REAL,
            mae_r REAL,
            close_price REAL,
            close_r REAL,
            capture_hour_utc INTEGER,
            primary_source TEXT,
            available_venues INTEGER,
            live_cvd_direction TEXT,
            live_cvd_pct REAL,
            market_bias TEXT,
            invalidation TEXT,
            blockers_json TEXT,
            warnings_json TEXT,
            quality_json TEXT,
            snapshot_json TEXT,
            signal_json TEXT,
            features_json TEXT
        )
        """)
        cols = {row[1] for row in db.execute("PRAGMA table_info(validation_setups)").fetchall()}
        if "setup_grade" not in cols:
            db.execute("ALTER TABLE validation_setups ADD COLUMN setup_grade TEXT")
        if "confidence_pct" not in cols:
            db.execute("ALTER TABLE validation_setups ADD COLUMN confidence_pct REAL")
        if "features_json" not in cols:
            db.execute("ALTER TABLE validation_setups ADD COLUMN features_json TEXT")

        db.execute("""
        CREATE INDEX IF NOT EXISTS idx_validation_status
        ON validation_setups(outcome, created_at)
        """)
        db.execute("""
        CREATE INDEX IF NOT EXISTS idx_validation_bucket
        ON validation_setups(direction, quality_grade, score)
        """)
        db.commit()

def capture_setup(snapshot: dict, signal: dict) -> tuple[bool, str]:
    direction = signal.get("directional_bias")
    state = signal.get("state")
    quality = signal.get("signal_quality") or {}
    adaptive = signal.get("adaptive_assessment") or {}
    features = extract_setup_features(snapshot, signal)
    entry = signal.get("entry_decision")
    score = signal.get("long_score", 0) if direction == "LONG" else signal.get("short_score", 0)

    if direction not in ("LONG", "SHORT"):
        return False, "NO_DIRECTION"
    if state not in ("WATCH", "SETUP_FORMING", "READY", "PAPER_SIGNAL"):
        return False, "STATE_NOT_CAPTURED"
    if int(score) < settings.validation_capture_min_score:
        return False, "SCORE_TOO_LOW"
    if quality.get("grade") not in ("MEDIUM", "HIGH"):
        return False, "QUALITY_TOO_LOW"
    if not entry:
        return False, "NO_ENTRY_PLAN"

    setup_id = signal["signal_id"]
    now = datetime.now(timezone.utc)
    with _connect() as db:
        # Deduplicate near-identical active setup: same direction, same strategy, within 15 min.
        existing = db.execute("""
            SELECT setup_id, entry_center
            FROM validation_setups
            WHERE direction=? AND strategy_version=?
              AND outcome IN ('WAITING_ENTRY','ACTIVE')
              AND created_at >= datetime('now', ?)
            ORDER BY created_at DESC LIMIT 1
        """, (
            direction,
            settings.strategy_version,
            f"-{settings.validation_capture_cooldown_minutes} minutes"
        )).fetchone()

        if existing:
            old = float(existing["entry_center"] or 0)
            new = float(entry.get("entry_center") or 0)
            pct = abs(new-old)/old*100 if old else 999
            if pct < settings.signal_dedupe_price_pct:
                return False, "VALIDATION_DUPLICATE"

        db.execute("""
        INSERT INTO validation_setups (
            setup_id, created_at, updated_at, strategy_version, symbol, direction,
            state_at_capture, quality_grade, setup_grade, confidence_pct,
            score, long_score, short_score, entry_low, entry_high, entry_center, stop, target1, target2, rr1, rr2,
            validity_minutes, outcome, mfe_price, mae_price, capture_hour_utc,
            primary_source, available_venues, live_cvd_direction, live_cvd_pct, features_json,
            market_bias, invalidation, blockers_json, warnings_json, quality_json,
            snapshot_json, signal_json, features_json
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            setup_id, now.isoformat(), now.isoformat(), settings.strategy_version,
            signal.get("symbol"), direction, state, quality.get("grade"),
            adaptive.get("setup_grade"), adaptive.get("confidence_pct"),
            int(score), int(signal.get("long_score",0)), int(signal.get("short_score",0)),
            entry.get("entry_low"), entry.get("entry_high"), entry.get("entry_center"),
            entry.get("stop"), entry.get("target1"), entry.get("target2"),
            entry.get("rr_target1"), entry.get("rr_target2"),
            entry.get("validity_minutes"), "WAITING_ENTRY",
            signal.get("price"), signal.get("price"), now.hour,
            snapshot.get("primary_source"), quality.get("available_venues"),
            quality.get("live_cvd_direction"), quality.get("live_cvd_pct"),
            signal.get("market_bias"), entry.get("invalidation"),
            json.dumps(signal.get("blockers",[]), separators=(",",":")),
            json.dumps(signal.get("warnings",[]), separators=(",",":")),
            json.dumps(quality, separators=(",",":")),
            json.dumps(snapshot, separators=(",",":")),
            json.dumps(signal, separators=(",",":")),
            json.dumps(features, separators=(",",":")),
        ))
        db.commit()
    return True, setup_id

def active_validation_setups():
    with _connect() as db:
        rows = db.execute("""
            SELECT * FROM validation_setups
            WHERE outcome IN ('WAITING_ENTRY','ACTIVE')
            ORDER BY created_at ASC
        """).fetchall()
    return [dict(r) for r in rows]

def update_validation(
    setup_id: str,
    *,
    outcome: str,
    price: float,
    entry_reached: bool | None = None,
    entry_fill_price: float | None = None,
    mfe_price: float | None = None,
    mae_price: float | None = None,
    mfe_r: float | None = None,
    mae_r: float | None = None,
    close_r: float | None = None,
):
    now = datetime.now(timezone.utc).isoformat()
    fields = ["outcome=?", "updated_at=?"]
    vals = [outcome, now]

    if entry_reached is not None:
        fields += ["entry_reached=?"]
        vals += [1 if entry_reached else 0]
        if entry_reached:
            fields += ["entry_reached_at=?"]
            vals += [now]

    if entry_fill_price is not None:
        fields += ["entry_fill_price=?"]
        vals += [entry_fill_price]
    if mfe_price is not None:
        fields += ["mfe_price=?"]
        vals += [mfe_price]
    if mae_price is not None:
        fields += ["mae_price=?"]
        vals += [mae_price]
    if mfe_r is not None:
        fields += ["mfe_r=?"]
        vals += [mfe_r]
    if mae_r is not None:
        fields += ["mae_r=?"]
        vals += [mae_r]

    if outcome not in ("WAITING_ENTRY","ACTIVE"):
        fields += ["outcome_at=?", "close_price=?", "close_r=?"]
        vals += [now, price, close_r]

    vals.append(setup_id)

    with _connect() as db:
        db.execute(
            f"UPDATE validation_setups SET {', '.join(fields)} WHERE setup_id=?",
            vals
        )
        db.commit()

def recent_validation(limit=50):
    limit = max(1, min(int(limit), 500))
    with _connect() as db:
        rows = db.execute("""
            SELECT setup_id, created_at, direction, state_at_capture, quality_grade,
                   setup_grade, confidence_pct, score, long_score, short_score, entry_low, entry_high, entry_center,
                   stop, target1, target2, rr1, rr2, entry_reached, entry_reached_at,
                   outcome, outcome_at, mfe_r, mae_r, close_r, capture_hour_utc,
                   primary_source, available_venues, live_cvd_direction, live_cvd_pct, features_json
            FROM validation_setups
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,)).fetchall()
    return [dict(r) for r in rows]


def validation_counts():
    with _connect() as db:
        return {
          "captured": db.execute("SELECT COUNT(*) FROM validation_setups").fetchone()[0],
          "waiting_entry": db.execute("SELECT COUNT(*) FROM validation_setups WHERE outcome='WAITING_ENTRY'").fetchone()[0],
          "active": db.execute("SELECT COUNT(*) FROM validation_setups WHERE outcome='ACTIVE'").fetchone()[0],
          "resolved": db.execute("SELECT COUNT(*) FROM validation_setups WHERE outcome IN ('TP1','TP2','STOPPED','EXPIRED')").fetchone()[0],
          "missed_entry": db.execute("SELECT COUNT(*) FROM validation_setups WHERE outcome='MISSED_ENTRY'").fetchone()[0],
        }
