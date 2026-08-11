import sqlite3
from datetime import datetime, timezone
from app.config import settings

def _connect():
    db = sqlite3.connect(settings.database_path)
    db.row_factory = sqlite3.Row
    return db

def init_push_db():
    with _connect() as db:
        db.execute("""
        CREATE TABLE IF NOT EXISTS push_devices (
            token TEXT PRIMARY KEY,
            platform TEXT NOT NULL,
            app_version TEXT,
            notifications_enabled INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """)
        db.commit()

def register_device(token: str, platform: str = "android", app_version: str = ""):
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as db:
        db.execute("""
        INSERT INTO push_devices(token, platform, app_version, notifications_enabled, created_at, updated_at)
        VALUES (?, ?, ?, 1, ?, ?)
        ON CONFLICT(token) DO UPDATE SET
            platform=excluded.platform,
            app_version=excluded.app_version,
            notifications_enabled=1,
            updated_at=excluded.updated_at
        """, (token, platform, app_version, now, now))
        db.commit()

def unregister_device(token: str):
    with _connect() as db:
        db.execute("UPDATE push_devices SET notifications_enabled=0, updated_at=? WHERE token=?",
                   (datetime.now(timezone.utc).isoformat(), token))
        db.commit()

def active_tokens():
    with _connect() as db:
        rows = db.execute("""
            SELECT token FROM push_devices
            WHERE notifications_enabled=1
            ORDER BY updated_at DESC
        """).fetchall()
    return [r["token"] for r in rows]

def push_device_stats():
    with _connect() as db:
        total = db.execute("SELECT COUNT(*) AS n FROM push_devices").fetchone()["n"]
        enabled = db.execute("SELECT COUNT(*) AS n FROM push_devices WHERE notifications_enabled=1").fetchone()["n"]
    return {"total_devices": total, "enabled_devices": enabled}
