import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

from app.config import settings

def load_events():
    path = Path(settings.event_file)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("events", [])
    except Exception:
        return []

def event_risk(now: datetime | None = None):
    now = now or datetime.now(timezone.utc)
    active = []
    upcoming = []

    for event in load_events():
        try:
            when = datetime.fromisoformat(event["datetime"])
            if when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
            when = when.astimezone(timezone.utc)
        except Exception:
            continue

        before = int(event.get("block_minutes_before", 30))
        after = int(event.get("block_minutes_after", 15))
        start = when - timedelta(minutes=before)
        end = when + timedelta(minutes=after)

        item = {
            "name": event.get("name", "High-impact event"),
            "datetime_utc": when.isoformat(),
            "source": event.get("source", ""),
            "minutes_until": round((when - now).total_seconds() / 60, 1),
        }

        if start <= now <= end:
            active.append(item)
        elif now < start:
            upcoming.append(item)

    upcoming.sort(key=lambda x: x["minutes_until"])
    return {
        "blocked": bool(active),
        "active_events": active,
        "next_event": upcoming[0] if upcoming else None,
    }
