from datetime import datetime, timezone, timedelta
import sqlite3
from app.config import settings

def should_store_candidate(db_path: str, signal: dict) -> tuple[bool, str]:
    direction = signal.get("candidate_opportunity")
    if direction not in ("LONG", "SHORT"):
        return True, "NON_CANDIDATE"

    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(minutes=settings.signal_cooldown_minutes)).isoformat()

    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    try:
        row = db.execute("""
            SELECT created_at, price, candidate
            FROM signals
            WHERE candidate=? AND created_at>=?
            ORDER BY created_at DESC
            LIMIT 1
        """, (direction, cutoff)).fetchone()
    finally:
        db.close()

    if not row:
        return True, "NEW_CANDIDATE"

    old_price = float(row["price"])
    new_price = float(signal["price"])
    pct = abs(new_price - old_price) / old_price * 100.0 if old_price else 999.0

    if pct < settings.signal_dedupe_price_pct:
        return False, f"COOLDOWN_DUPLICATE_{direction}_{pct:.3f}%"
    return True, f"PRICE_MOVED_{pct:.3f}%"
