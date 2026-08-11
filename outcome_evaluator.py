import asyncio
from datetime import datetime, timezone
from app.services.market_source import fetch_last_price_resilient
from app.services.storage import active_signals, update_outcome

def evaluate_one(row: dict, price: float):
    direction = row["candidate"]
    stop = float(row["stop"])
    t1 = float(row["target1"])
    t2 = float(row["target2"])
    expires_at = datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None
    now = datetime.now(timezone.utc)

    # Conservative intrapoll ordering: stop is checked before target because
    # we do not know the exact tick path between polls.
    if direction == "LONG":
        if price <= stop:
            return "STOPPED"
        if price >= t2:
            return "TP2"
        if price >= t1:
            return "TP1"
    else:
        if price >= stop:
            return "STOPPED"
        if price <= t2:
            return "TP2"
        if price <= t1:
            return "TP1"

    if expires_at and now >= expires_at.astimezone(timezone.utc):
        return "EXPIRED"
    return "ACTIVE"

async def evaluate_active_once():
    rows = active_signals()
    if not rows:
        return {"checked": 0, "price": None}

    price = await fetch_last_price_resilient()
    for row in rows:
        outcome = evaluate_one(row, price)
        update_outcome(row["signal_id"], outcome, price)
    return {"checked": len(rows), "price": price}

async def outcome_loop():
    while True:
        try:
            await evaluate_active_once()
        except asyncio.CancelledError:
            raise
        except Exception:
            pass
        await asyncio.sleep(15)
