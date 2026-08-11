import json
import os
import sqlite3
from datetime import datetime, timezone
from app.config import settings

def ensure_persistent_storage():
    data_dir = settings.persistent_data_dir
    os.makedirs(data_dir, exist_ok=True)

    # Verify the directory is writable.
    probe_path = settings.persistent_probe_file
    payload = {
        "last_start_utc": datetime.now(timezone.utc).isoformat(),
        "database_path": settings.database_path,
    }

    previous = None
    if os.path.exists(probe_path):
        try:
            with open(probe_path, "r", encoding="utf-8") as fh:
                previous = json.load(fh)
        except Exception:
            previous = None

    with open(probe_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, separators=(",", ":"))

    # Touch database and enable WAL mode for better durability/concurrency.
    with sqlite3.connect(settings.database_path) as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=NORMAL")
        db.execute("CREATE TABLE IF NOT EXISTS persistence_meta (key TEXT PRIMARY KEY, value TEXT)")
        db.execute(
            "INSERT OR REPLACE INTO persistence_meta(key,value) VALUES (?,?)",
            ("last_start_utc", payload["last_start_utc"])
        )
        db.commit()

    return {
        "data_dir": data_dir,
        "database_path": settings.database_path,
        "probe_path": probe_path,
        "previous_probe": previous,
        "current_probe": payload,
        "database_exists": os.path.exists(settings.database_path),
        "database_size_bytes": os.path.getsize(settings.database_path) if os.path.exists(settings.database_path) else 0,
    }

def persistence_status():
    probe = None
    if os.path.exists(settings.persistent_probe_file):
        try:
            with open(settings.persistent_probe_file, "r", encoding="utf-8") as fh:
                probe = json.load(fh)
        except Exception:
            probe = None

    db_exists = os.path.exists(settings.database_path)
    db_size = os.path.getsize(settings.database_path) if db_exists else 0

    counts = {}
    if db_exists:
        try:
            with sqlite3.connect(settings.database_path) as db:
                for table in ("signals", "validation_setups", "push_devices"):
                    try:
                        counts[table] = db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                    except Exception:
                        counts[table] = None
        except Exception:
            pass

    return {
        "persistent_data_dir": settings.persistent_data_dir,
        "database_path": settings.database_path,
        "probe_file": settings.persistent_probe_file,
        "probe": probe,
        "database_exists": db_exists,
        "database_size_bytes": db_size,
        "table_counts": counts,
        "writable": os.access(settings.persistent_data_dir, os.W_OK),
    }
