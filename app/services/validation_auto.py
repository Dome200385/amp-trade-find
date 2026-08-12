import asyncio
from datetime import datetime, timezone

from app.config import settings
from app.services.market import build_market_snapshot
from app.services.engine import calculate_signal
from app.services.validation_storage import capture_setup
from app.services.validation_evaluator import evaluate_validation_once
from app.services.validation_storage import validation_counts

STATE_RANK = {
    "NO_TRADE": 0,
    "WATCH": 1,
    "SETUP_FORMING": 2,
    "READY": 3,
    "PAPER_SIGNAL": 4,
}

_last_scan = {
    "at": None,
    "captured": False,
    "reason": "NOT_RUN",
    "state": None,
    "direction": None,
    "long_score": None,
    "short_score": None,
    "quality_grade": None,
    "error": None,
}

def _passes_capture_policy(signal: dict) -> tuple[bool, str]:
    if not settings.validation_auto_capture_enabled:
        return False, "AUTO_CAPTURE_DISABLED"

    state = signal.get("state", "NO_TRADE")
    min_state = settings.validation_min_state
    if STATE_RANK.get(state, 0) < STATE_RANK.get(min_state, 2):
        return False, f"STATE_BELOW_{min_state}"

    direction = signal.get("directional_bias")
    if direction not in ("LONG", "SHORT"):
        return False, "NO_DIRECTION"

    quality = signal.get("signal_quality") or {}
    if quality.get("grade") not in ("MEDIUM", "HIGH"):
        return False, "QUALITY_TOO_LOW"

    if settings.validation_require_cross_market:
        if direction == "LONG" and not quality.get("cross_market_long", False):
            return False, "NO_CROSS_MARKET_LONG"
        if direction == "SHORT" and not quality.get("cross_market_short", False):
            return False, "NO_CROSS_MARKET_SHORT"

    if settings.validation_require_entry_plan and not signal.get("entry_decision"):
        return False, "NO_ENTRY_PLAN"

    return True, "POLICY_OK"

def _learning_policy(signal, counts):
    if not settings.learning_capture_enabled: return False, "LEARNING_CAPTURE_DISABLED"
    if counts["active"] + counts["waiting_entry"] >= settings.collector_max_active_setups: return False, "MAX_ACTIVE_SETUPS_REACHED"
    rank={"NO_TRADE":0,"WATCH":1,"SETUP_FORMING":2,"READY":3,"PAPER_SIGNAL":4}
    state=signal.get("state","NO_TRADE"); direction=signal.get("directional_bias","NONE"); q=signal.get("signal_quality") or {}
    if rank.get(state,0) < rank.get(settings.learning_capture_min_state,1): return False,"LEARNING_STATE_TOO_LOW"
    if direction not in ("LONG","SHORT"): return False,"LEARNING_NO_DIRECTION"
    score=int(signal.get("long_score",0) if direction=="LONG" else signal.get("short_score",0))
    if score < settings.learning_capture_min_score: return False,"LEARNING_SCORE_TOO_LOW"
    if not settings.learning_capture_allow_low_quality and q.get("grade") not in ("MEDIUM","HIGH"): return False,"LEARNING_QUALITY_TOO_LOW"
    if settings.learning_capture_require_entry_plan and not signal.get("entry_decision"): return False,"LEARNING_NO_ENTRY_PLAN"
    return True,"LEARNING_POLICY_OK"

async def auto_scan_once():
    global _last_scan

    snapshot = await build_market_snapshot()
    signal = calculate_signal(snapshot)

    ok, reason = _passes_capture_policy(signal)
    captured = False
    capture_reason = reason

    if ok:
        captured, capture_reason = capture_setup(snapshot, signal, capture_tier="STRICT")
    else:
        learn_ok, learn_reason = _learning_policy(signal, validation_counts())
        if learn_ok:
            captured, capture_reason = capture_setup(snapshot, signal, capture_tier="LEARNING", strict_rejection_reason=reason)
        else:
            capture_reason = f"{reason}|{learn_reason}"

    # Also advance already captured setups every scan.
    eval_result = await evaluate_validation_once()

    _last_scan = {
        "at": datetime.now(timezone.utc).isoformat(),
        "captured": captured,
        "reason": capture_reason,
        "state": signal.get("state"),
        "direction": signal.get("directional_bias"),
        "long_score": signal.get("long_score"),
        "short_score": signal.get("short_score"),
        "quality_grade": (signal.get("signal_quality") or {}).get("grade"),
        "entry_decision": signal.get("entry_decision"),
        "evaluation": eval_result,
        "error": None,
    }
    return _last_scan

async def validation_auto_loop():
    while True:
        try:
            await auto_scan_once()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            _last_scan.update({
                "at": datetime.now(timezone.utc).isoformat(),
                "captured": False,
                "reason": "SCAN_ERROR",
                "error": str(exc)[:300],
            })
        await asyncio.sleep(settings.validation_scan_seconds)

def validation_auto_status():
    return {
        "enabled": settings.validation_auto_capture_enabled,
        "scan_seconds": settings.validation_scan_seconds,
        "minimum_state": settings.validation_min_state,
        "require_cross_market": settings.validation_require_cross_market,
        "require_entry_plan": settings.validation_require_entry_plan,
        "last_scan": _last_scan,
    }
