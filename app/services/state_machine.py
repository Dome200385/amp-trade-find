from datetime import datetime, timezone, timedelta
from app.config import settings

# In-memory state is enough for V8.4 on one Render instance.
# Persistent state can move to Postgres in a later version.
_state = {
    "state": "NO_TRADE",
    "direction": "NONE",
    "since": datetime.now(timezone.utc),
    "last_score": 0,
    "last_reason": "INIT",
}

ORDER = {
    "NO_TRADE": 0,
    "WATCH": 1,
    "SETUP_FORMING": 2,
    "READY": 3,
    "PAPER_SIGNAL": 4,
}

def _age_minutes(now):
    return (now - _state["since"]).total_seconds() / 60.0

def _set(new_state, direction, score, reason):
    now = datetime.now(timezone.utc)
    changed = new_state != _state["state"] or direction != _state["direction"]
    if changed:
        _state["state"] = new_state
        _state["direction"] = direction
        _state["since"] = now
    _state["last_score"] = score
    _state["last_reason"] = reason
    return changed

def transition(
    *,
    candidate_direction: str,
    directional_score: int,
    quality_grade: str,
    cross_market_confirmed: bool,
    live_cvd_matches: bool,
    timing_matches: bool,
    event_blocked: bool,
    blockers: list[str],
    entry_decision: dict | None,
):
    now = datetime.now(timezone.utc)

    hard_blockers = {
        "HIGH_IMPACT_EVENT",
        "INSUFFICIENT_VENUES",
        "SPOT_DERIVATIVES_CONFLICT",
        "LOW_SIGNAL_QUALITY",
        "LIVE_CVD_NOT_READY",
    }
    hard_blocked = event_blocked or any(b in hard_blockers for b in blockers)

    direction = candidate_direction if candidate_direction in ("LONG", "SHORT") else "NONE"

    if hard_blocked:
        new_state = "NO_TRADE"
        reason = "HARD_BLOCKER"
        direction = "NONE"
    elif directional_score < settings.watch_threshold:
        new_state = "NO_TRADE"
        reason = "SCORE_BELOW_WATCH"
        direction = "NONE"
    elif directional_score < settings.setup_threshold:
        new_state = "WATCH"
        reason = "DIRECTIONAL_INTEREST"
    elif quality_grade not in ("HIGH", "MEDIUM"):
        new_state = "WATCH"
        reason = "QUALITY_NOT_READY"
    elif not cross_market_confirmed:
        new_state = "SETUP_FORMING"
        reason = "WAITING_CROSS_MARKET_CONFIRMATION"
    elif not live_cvd_matches or not timing_matches:
        new_state = "SETUP_FORMING"
        reason = "WAITING_TRIGGER_CONFIRMATION"
    elif directional_score < settings.ready_min_score:
        new_state = "SETUP_FORMING"
        reason = "SCORE_BELOW_READY"
    elif not entry_decision or not entry_decision.get("valid"):
        new_state = "SETUP_FORMING"
        reason = "ENTRY_PLAN_INVALID"
    elif not entry_decision.get("entry_now"):
        new_state = "READY"
        reason = "WAITING_FOR_ENTRY_ZONE"
    elif directional_score < settings.paper_signal_min_score:
        new_state = "READY"
        reason = "READY_BUT_SCORE_BELOW_SIGNAL"
    else:
        new_state = "PAPER_SIGNAL"
        reason = "ALL_CONFIRMATIONS_MET"

    # Expire stale non-signal state memory.
    if (
        _state["state"] in ("WATCH", "SETUP_FORMING", "READY")
        and _age_minutes(now) >= settings.state_memory_minutes
        and ORDER.get(new_state, 0) <= ORDER.get(_state["state"], 0)
    ):
        new_state = "NO_TRADE"
        direction = "NONE"
        reason = "STATE_EXPIRED"

    changed = _set(new_state, direction, directional_score, reason)

    return {
        "state": new_state,
        "direction": direction,
        "changed": changed,
        "since_utc": _state["since"].isoformat(),
        "age_minutes": round(_age_minutes(now), 2),
        "score": directional_score,
        "reason": reason,
    }
