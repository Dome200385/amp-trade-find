import asyncio
from datetime import datetime, timezone
from app.config import settings
from app.services.market import build_market_snapshot
from app.services.engine import calculate_signal
from app.services.validation_storage import capture_setup, validation_counts
from app.services.validation_evaluator import evaluate_validation_once
from app.services.collector_storage import record_run, collector_stats

_status={"started_at_utc":datetime.now(timezone.utc).isoformat(),"last_cycle_at_utc":None,"last_error":None}

def _policy(signal,counts):
    if counts["active"]+counts["waiting_entry"]>=settings.collector_max_active_setups: return False,"MAX_ACTIVE_SETUPS_REACHED"
    state=signal.get("state","NO_TRADE"); direction=signal.get("directional_bias","NONE"); q=signal.get("signal_quality") or {}
    if state not in ("SETUP_FORMING","READY","PAPER_SIGNAL"): return False,"STATE_BELOW_CAPTURE"
    if direction not in ("LONG","SHORT"): return False,"NO_DIRECTION"
    if q.get("grade") not in ("MEDIUM","HIGH"): return False,"QUALITY_TOO_LOW"
    if not signal.get("entry_decision"): return False,"NO_ENTRY_PLAN"
    if direction=="LONG" and not q.get("cross_market_long",False): return False,"NO_CROSS_MARKET_LONG"
    if direction=="SHORT" and not q.get("cross_market_short",False): return False,"NO_CROSS_MARKET_SHORT"
    return True,"POLICY_OK"

async def collector_cycle():
    evaluation=await evaluate_validation_once()
    snapshot=await build_market_snapshot()
    signal=calculate_signal(snapshot)
    counts=validation_counts()
    ok,reason=_policy(signal,counts); captured=False; capture_reason=reason
    if ok: captured,capture_reason=capture_setup(snapshot,signal)
    counts=validation_counts(); q=signal.get("signal_quality") or {}
    record_run(state=signal.get("state"),direction=signal.get("directional_bias"),
      quality_grade=q.get("grade"),long_score=signal.get("long_score"),short_score=signal.get("short_score"),
      captured=captured,capture_reason=capture_reason,primary_source=snapshot.get("primary_source"),
      available_venues=q.get("available_venues"),active_validation_setups=counts["active"]+counts["waiting_entry"])
    _status.update({"last_cycle_at_utc":datetime.now(timezone.utc).isoformat(),"last_error":None,
      "last_capture":captured,"last_reason":capture_reason,"state":signal.get("state"),
      "direction":signal.get("directional_bias"),"long_score":signal.get("long_score"),
      "short_score":signal.get("short_score"),"quality_grade":q.get("grade"),
      "validation_counts":counts,"evaluation":evaluation})
    return dict(_status)

async def collector_loop():
    while True:
        try: await collector_cycle()
        except asyncio.CancelledError: raise
        except Exception as exc:
            _status.update({"last_cycle_at_utc":datetime.now(timezone.utc).isoformat(),
              "last_error":str(exc)[:300],"last_capture":False,"last_reason":"COLLECTOR_ERROR"})
            try: record_run(captured=False,capture_reason="COLLECTOR_ERROR",error=str(exc)[:300])
            except Exception: pass
        await asyncio.sleep(settings.collector_heartbeat_seconds)

def collector_status():
    counts=validation_counts(); target=settings.collector_progress_target; resolved=counts["resolved"]
    return {**_status,"heartbeat_seconds":settings.collector_heartbeat_seconds,
      "max_active_setups":settings.collector_max_active_setups,
      "progress":{"target_resolved_samples":target,"resolved_samples":resolved,
        "remaining":max(target-resolved,0),"progress_pct":round(min(resolved/target*100,100),2) if target else 100},
      "validation_counts":counts,"stats_24h":collector_stats(settings.collector_stats_window_hours)}
