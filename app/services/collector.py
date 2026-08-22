import asyncio
from datetime import datetime, timezone
from app.config import settings
from app.services.market import build_market_snapshot
from app.services.engine import calculate_signal
from app.services.validation_storage import capture_setup, validation_counts
from app.services.validation_evaluator import evaluate_validation_once
from app.services.collector_storage import record_run, collector_stats
from app.services.learning_funnel import record_funnel_run, funnel_stats
from app.services.observation_learning import capture_observation, evaluate_observations
from app.services.v99_filter import evaluate_v99_filter

_status={"started_at_utc":datetime.now(timezone.utc).isoformat(),"last_cycle_at_utc":None,"last_error":None}

def _policy(signal,counts):
    if counts["active"]+counts["waiting_entry"]>=settings.collector_max_active_setups:
        return False,"MAX_ACTIVE_SETUPS_REACHED"
    state=signal.get("state","NO_TRADE")
    direction=signal.get("directional_bias","NONE")
    q=signal.get("signal_quality") or {}
    if state not in ("SETUP_FORMING","READY","PAPER_SIGNAL"):
        return False,"STATE_BELOW_CAPTURE"
    if direction not in ("LONG","SHORT"):
        return False,"NO_DIRECTION"
    if q.get("grade") not in ("MEDIUM","HIGH"):
        return False,"QUALITY_TOO_LOW"
    if not signal.get("entry_decision"):
        return False,"NO_ENTRY_PLAN"
    if direction=="LONG" and not q.get("cross_market_long",False):
        return False,"NO_CROSS_MARKET_LONG"
    if direction=="SHORT" and not q.get("cross_market_short",False):
        return False,"NO_CROSS_MARKET_SHORT"
    return True,"POLICY_OK"

def _learning_policy(signal, counts):
    if not settings.learning_capture_enabled:
        return False,"LEARNING_CAPTURE_DISABLED"
    if counts["active"]+counts["waiting_entry"]>=settings.collector_max_active_setups:
        return False,"MAX_ACTIVE_SETUPS_REACHED"
    state=signal.get("state","NO_TRADE")
    direction=signal.get("directional_bias","NONE")
    q=signal.get("signal_quality") or {}
    rank={"NO_TRADE":0,"WATCH":1,"SETUP_FORMING":2,"READY":3,"PAPER_SIGNAL":4}
    if rank.get(state,0)<rank.get(settings.learning_capture_min_state,1):
        return False,"LEARNING_STATE_TOO_LOW"
    if direction not in ("LONG","SHORT"):
        return False,"LEARNING_NO_DIRECTION"
    score=int(signal.get("long_score",0) if direction=="LONG" else signal.get("short_score",0))
    if score<settings.learning_capture_min_score:
        return False,"LEARNING_SCORE_TOO_LOW"
    if not settings.learning_capture_allow_low_quality and q.get("grade") not in ("MEDIUM","HIGH"):
        return False,"LEARNING_QUALITY_TOO_LOW"
    if settings.learning_capture_require_entry_plan and not signal.get("entry_decision"):
        return False,"LEARNING_NO_ENTRY_PLAN"
    if settings.learning_capture_require_cross_market:
        if direction=="LONG" and not q.get("cross_market_long",False):
            return False,"LEARNING_NO_CROSS_MARKET_LONG"
        if direction=="SHORT" and not q.get("cross_market_short",False):
            return False,"LEARNING_NO_CROSS_MARKET_SHORT"
    return True,"LEARNING_POLICY_OK"

async def collector_cycle():
    evaluation=await evaluate_validation_once()
    snapshot=await build_market_snapshot()
    signal=calculate_signal(snapshot)
    observation_evaluation=evaluate_observations(snapshot.get("price")) if snapshot.get("price") is not None else {"checked":0,"updates":[]}
    counts=validation_counts()

    strict_ok, strict_reason=_policy(signal,counts)
    learning_ok, learning_reason=_learning_policy(signal,counts)
    v99_filter=evaluate_v99_filter(snapshot,signal)
    if v99_filter.get("blocked"):
        if strict_ok:
            strict_ok=False
            strict_reason="V99_FORWARD_WEAK_BUCKET"
        if learning_ok:
            learning_ok=False
            learning_reason="V99_FORWARD_WEAK_BUCKET"

    captured=False
    capture_reason=strict_reason
    capture_tier="NONE"

    if strict_ok:
        captured,capture_reason=capture_setup(snapshot,signal,capture_tier="STRICT")
        if captured:
            capture_tier="STRICT"
    elif learning_ok:
        captured,capture_reason=capture_setup(
            snapshot,signal,
            capture_tier="LEARNING",
            strict_rejection_reason=strict_reason
        )
        if captured:
            capture_tier="LEARNING"
    else:
        capture_reason=f"{strict_reason}|{learning_reason}"

    observation_captured=False
    observation_reason="STRICT_OR_LEARNING_CAPTURE"
    if not captured:
        observation_captured,observation_reason=capture_observation(snapshot,signal,capture_reason)

    record_funnel_run(
        signal=signal,
        strict_ok=strict_ok,
        strict_reason=strict_reason,
        learning_ok=learning_ok,
        learning_reason=learning_reason,
        captured=captured,
        capture_mode=capture_tier if capture_tier!="NONE" else None,
        capture_reason=capture_reason,
    )

    counts=validation_counts()
    q=signal.get("signal_quality") or {}
    record_run(
        state=signal.get("state"),
        direction=signal.get("directional_bias"),
        quality_grade=q.get("grade"),
        long_score=signal.get("long_score"),
        short_score=signal.get("short_score"),
        captured=captured,
        capture_reason=capture_reason,
        primary_source=snapshot.get("primary_source"),
        available_venues=q.get("available_venues"),
        active_validation_setups=counts["active"]+counts["waiting_entry"]
    )
    _status.update({
        "last_cycle_at_utc":datetime.now(timezone.utc).isoformat(),
        "last_error":None,
        "last_capture":captured,
        "last_reason":capture_reason,
        "state":signal.get("state"),
        "direction":signal.get("directional_bias"),
        "long_score":signal.get("long_score"),
        "short_score":signal.get("short_score"),
        "quality_grade":q.get("grade"),
        "capture_tier":capture_tier,
        "validation_counts":counts,
        "evaluation":evaluation,
        "observation_evaluation":observation_evaluation,
        "observation_captured":observation_captured,
        "observation_reason":observation_reason,
        "v99_filter":v99_filter
    })
    return dict(_status)

async def collector_loop():
    while True:
        try:
            await collector_cycle()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            _status.update({
                "last_cycle_at_utc":datetime.now(timezone.utc).isoformat(),
                "last_error":str(exc)[:300],
                "last_capture":False,
                "last_reason":"COLLECTOR_ERROR"
            })
            try:
                record_run(captured=False,capture_reason="COLLECTOR_ERROR",error=str(exc)[:300])
            except Exception:
                pass
        await asyncio.sleep(settings.collector_heartbeat_seconds)

def collector_status():
    counts=validation_counts()
    target=settings.collector_progress_target
    resolved=counts["resolved"]
    return {
        **_status,
        "heartbeat_seconds":settings.collector_heartbeat_seconds,
        "max_active_setups":settings.collector_max_active_setups,
        "progress":{
            "target_resolved_samples":target,
            "resolved_samples":resolved,
            "remaining":max(target-resolved,0),
            "progress_pct":round(min(resolved/target*100,100),2) if target else 100
        },
        "validation_counts":counts,
        "stats_24h":collector_stats(settings.collector_stats_window_hours),
        "funnel_24h":funnel_stats(24)
    }
