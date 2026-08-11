import json
from app.config import settings
from app.services.push_storage import active_tokens, push_device_stats

_initialized = False
_init_error = None

def _initialize():
    global _initialized, _init_error
    if _initialized:
        return True
    if not settings.firebase_enabled:
        _init_error = "FIREBASE_DISABLED"
        return False
    if not settings.firebase_service_account_json.strip():
        _init_error = "FIREBASE_CREDENTIALS_MISSING"
        return False

    try:
        import firebase_admin
        from firebase_admin import credentials

        if not firebase_admin._apps:
            raw = json.loads(settings.firebase_service_account_json)
            firebase_admin.initialize_app(credentials.Certificate(raw))
        _initialized = True
        _init_error = None
        return True
    except Exception as exc:
        _init_error = str(exc)[:300]
        return False

def status():
    ok = _initialize()
    return {
        "configured": settings.firebase_enabled,
        "ready": ok,
        "error": _init_error,
        **push_device_stats(),
    }

def send_signal_payload(payload: dict):
    if not _initialize():
        return {"sent": 0, "failed": 0, "status": "NOT_READY", "error": _init_error}

    from firebase_admin import messaging

    tokens = active_tokens()
    if not tokens:
        return {"sent": 0, "failed": 0, "status": "NO_DEVICES"}

    data = {
        "type": "find_signal",
        "signal_id": str(payload.get("signal_id") or ""),
        "direction": str(payload.get("direction") or "NONE"),
        "state": str(payload.get("state") or ""),
        "long_score": str(payload.get("long_score") or 0),
        "short_score": str(payload.get("short_score") or 0),
        "deep_link": str(payload.get("deep_link") or ""),
        "paper_mode": str(bool(payload.get("paper_mode", True))).lower(),
    }

    message = messaging.MulticastMessage(
        notification=messaging.Notification(
            title=str(payload.get("title") or "AMP TRADE FIND"),
            body=str(payload.get("body") or ""),
        ),
        data=data,
        tokens=tokens[:500],
        android=messaging.AndroidConfig(
            priority="high",
            ttl=60,
            notification=messaging.AndroidNotification(
                channel_id="amp_find_signals",
                sound="default",
            ),
        ),
    )

    result = messaging.send_each_for_multicast(message)
    return {
        "sent": result.success_count,
        "failed": result.failure_count,
        "status": "SENT",
    }
