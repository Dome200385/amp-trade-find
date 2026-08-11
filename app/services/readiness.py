import sqlite3
from app.config import settings
from app.services.live_cvd import live_cvd
from app.services.firebase_push import status as push_status
from app.services.persistence import persistence_status

def check_readiness():
    db_ok = False
    db_error = None
    try:
        with sqlite3.connect(settings.database_path) as db:
            db.execute("SELECT 1").fetchone()
        db_ok = True
    except Exception as exc:
        db_error = str(exc)[:240]

    cvd = live_cvd.snapshot()
    # WebSocket can still be warming up; it is reported but does not fail service readiness.
    ready = db_ok

    return {
        "ready": ready,
        "database": {"ok": db_ok, "error": db_error},
        "live_cvd": {
            "connected": cvd.get("connected", False),
            "buffered_trades": cvd.get("buffered_trades", 0),
            "last_error": cvd.get("last_error"),
        },
        "push": push_status(),
        "persistence": persistence_status(),
    }
