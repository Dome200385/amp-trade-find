import asyncio
from datetime import datetime, timezone, timedelta
from app.config import settings
from app.services.market_source import fetch_last_price_resilient
from app.services.validation_storage import active_validation_setups, update_validation

def _dt(s):
    return datetime.fromisoformat(s).astimezone(timezone.utc)

def _r(direction, entry, price, risk):
    if not risk:
        return 0.0
    pnl = (price-entry) if direction == "LONG" else (entry-price)
    return pnl/risk

def evaluate_row(row: dict, price: float, now=None):
    now = now or datetime.now(timezone.utc)
    direction = row["direction"]
    entry_low = float(row["entry_low"])
    entry_high = float(row["entry_high"])
    entry_center = float(row["entry_center"])
    stop = float(row["stop"])
    t1 = float(row["target1"])
    t2 = float(row["target2"])
    risk = abs(entry_center-stop)
    created = _dt(row["created_at"])
    entry_reached = bool(row["entry_reached"])
    fill = float(row["entry_fill_price"]) if row["entry_fill_price"] is not None else entry_center

    # Waiting for entry.
    if not entry_reached:
        if entry_low <= price <= entry_high:
            return {
                "outcome":"ACTIVE", "entry_reached":True,
                "entry_fill_price":price,
                "mfe_price":price, "mae_price":price,
                "mfe_r":0.0, "mae_r":0.0, "close_r":None
            }
        if now >= created + timedelta(minutes=settings.validation_entry_timeout_minutes):
            return {
                "outcome":"MISSED_ENTRY", "entry_reached":False,
                "entry_fill_price":None, "mfe_price":row["mfe_price"],
                "mae_price":row["mae_price"], "mfe_r":None, "mae_r":None, "close_r":0.0
            }
        return {"outcome":"WAITING_ENTRY"}

    # Active trade.
    mfe_price = float(row["mfe_price"]) if row["mfe_price"] is not None else fill
    mae_price = float(row["mae_price"]) if row["mae_price"] is not None else fill

    if direction == "LONG":
        mfe_price = max(mfe_price, price)
        mae_price = min(mae_price, price)
        if price <= stop:
            outcome = "STOPPED"
        elif price >= t2:
            outcome = "TP2"
        elif price >= t1:
            outcome = "TP1"
        else:
            outcome = "ACTIVE"
    else:
        mfe_price = min(mfe_price, price)
        mae_price = max(mae_price, price)
        if price >= stop:
            outcome = "STOPPED"
        elif price <= t2:
            outcome = "TP2"
        elif price <= t1:
            outcome = "TP1"
        else:
            outcome = "ACTIVE"

    mfe_r = _r(direction, fill, mfe_price, risk)
    mae_r = _r(direction, fill, mae_price, risk)

    if outcome != "ACTIVE":
        close_r = _r(direction, fill, price, risk)
        # Normalize target/stop results for less polling noise.
        if outcome == "STOPPED": close_r = -1.0
        elif outcome == "TP1": close_r = float(row["rr1"] or 1.5)
        elif outcome == "TP2": close_r = float(row["rr2"] or 2.2)
        return {
            "outcome":outcome, "entry_reached":True, "entry_fill_price":fill,
            "mfe_price":mfe_price, "mae_price":mae_price,
            "mfe_r":mfe_r, "mae_r":mae_r, "close_r":close_r
        }

    entered_at = _dt(row["entry_reached_at"]) if row["entry_reached_at"] else created
    if now >= entered_at + timedelta(minutes=settings.validation_trade_timeout_minutes):
        return {
            "outcome":"EXPIRED", "entry_reached":True, "entry_fill_price":fill,
            "mfe_price":mfe_price, "mae_price":mae_price,
            "mfe_r":mfe_r, "mae_r":mae_r,
            "close_r":_r(direction, fill, price, risk)
        }

    return {
        "outcome":"ACTIVE", "entry_reached":True, "entry_fill_price":fill,
        "mfe_price":mfe_price, "mae_price":mae_price,
        "mfe_r":mfe_r, "mae_r":mae_r, "close_r":None
    }

async def evaluate_validation_once():
    rows = active_validation_setups()
    if not rows:
        return {"checked":0, "price":None, "updates":[]}

    price = await fetch_last_price_resilient()
    updates = []
    now = datetime.now(timezone.utc)

    for row in rows:
        result = evaluate_row(row, price, now)
        if result["outcome"] == "WAITING_ENTRY":
            continue
        update_validation(
            row["setup_id"],
            outcome=result["outcome"],
            price=price,
            entry_reached=result.get("entry_reached"),
            entry_fill_price=result.get("entry_fill_price"),
            mfe_price=result.get("mfe_price"),
            mae_price=result.get("mae_price"),
            mfe_r=result.get("mfe_r"),
            mae_r=result.get("mae_r"),
            close_r=result.get("close_r"),
        )
        updates.append({"setup_id":row["setup_id"], "outcome":result["outcome"]})

    return {"checked":len(rows), "price":price, "updates":updates}

async def validation_loop():
    while True:
        try:
            await evaluate_validation_once()
        except asyncio.CancelledError:
            raise
        except Exception:
            pass
        await asyncio.sleep(settings.validation_poll_seconds)
