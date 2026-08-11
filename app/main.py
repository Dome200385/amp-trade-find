import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import settings
from app.models.schemas import MarketSnapshot, SignalResponse
from app.services.market import build_market_snapshot
from app.services.engine import calculate_signal
from app.services.storage import init_db, save_signal, recent_signals, performance_stats, get_signal_detail
from app.services.live_cvd import run_bybit_trade_stream, live_cvd
from app.services.outcome_evaluator import outcome_loop, evaluate_active_once
from app.services.event_risk import event_risk
from app.services.signal_gate import should_store_candidate
from app.services.bybit import get_kline_history
from app.services.backtest import run_backtest, summarize
from app.services.validation import walk_forward
from app.services.dashboard import build_dashboard
from app.services.push_storage import init_push_db, register_device, unregister_device
from app.services.firebase_push import status as firebase_status, send_signal_payload
from app.services.readiness import check_readiness
from app.services.notification_payload import build_notification_payload


class PushRegisterRequest(BaseModel):
    token: str
    platform: str = "android"
    app_version: str = ""

class PushUnregisterRequest(BaseModel):
    token: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    init_push_db()
    ws_task = asyncio.create_task(run_bybit_trade_stream())
    outcome_task = asyncio.create_task(outcome_loop())
    yield
    ws_task.cancel()
    outcome_task.cancel()
    await asyncio.gather(ws_task, outcome_task, return_exceptions=True)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Bitcoin opportunity intelligence backend for AMP TRADE FIND.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "strategy_version": settings.strategy_version,
        "status": "online",
        "mode": "paper-analysis",
        "live_cvd_connected": live_cvd.connected,
    }

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "time_utc": datetime.now(timezone.utc).isoformat(),
        "live_cvd": live_cvd.snapshot(),
    }


@app.get("/ready")
async def ready():
    result = check_readiness()
    if not result["ready"]:
        raise HTTPException(status_code=503, detail=result)
    return result

@app.get("/api/v1/push/status")
async def push_status():
    return firebase_status()

@app.post("/api/v1/push/register")
async def push_register(body: PushRegisterRequest):
    token = body.token.strip()
    if len(token) < 20:
        raise HTTPException(status_code=400, detail="Invalid FCM token")
    register_device(token, body.platform, body.app_version)
    return {"registered": True}

@app.post("/api/v1/push/unregister")
async def push_unregister(body: PushUnregisterRequest):
    unregister_device(body.token.strip())
    return {"unregistered": True}

@app.post("/api/v1/push/test")
async def push_test(x_admin_key: str | None = Header(default=None)):
    if not settings.admin_api_key or x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=403, detail="Admin key required")
    payload = {
        "title": "AMP FIND · PUSH TEST",
        "body": "Push-Verbindung funktioniert.",
        "signal_id": "PUSH-TEST",
        "direction": "NONE",
        "state": "TEST",
        "long_score": 0,
        "short_score": 0,
        "deep_link": "amptradefind://signal/PUSH-TEST",
        "paper_mode": True,
    }
    return send_signal_payload(payload)

@app.get("/api/v1/market/snapshot", response_model=MarketSnapshot)
async def market_snapshot():
    try:
        return await build_market_snapshot()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Market data unavailable: {exc}") from exc

@app.get("/api/v1/signal", response_model=SignalResponse)
async def signal():
    try:
        snapshot = await build_market_snapshot()
        result = calculate_signal(snapshot)
        allowed, reason = should_store_candidate(settings.database_path, result)
        result["gate_reason"] = reason

        if allowed:
            save_signal(snapshot, result)
        else:
            result["blockers"].append("SIGNAL_COOLDOWN_DUPLICATE")
            result["candidate_opportunity"] = "NONE"
            result["trade_plan"] = None
        return result
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Signal engine unavailable: {exc}") from exc

@app.get("/api/v1/signals/recent")
async def signals_recent(limit: int = Query(default=50, ge=1, le=500)):
    rows = recent_signals(limit)
    return {"signals": rows, "count": len(rows)}


@app.get("/api/v1/signals/{signal_id}")
async def signal_detail(signal_id: str):
    row = get_signal_detail(signal_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Signal not found")
    return row

@app.get("/api/v1/performance")
async def performance():
    return performance_stats()

@app.get("/api/v1/events/risk")
async def events_risk():
    return event_risk()

@app.get("/api/v1/live/cvd")
async def live_cvd_status():
    return live_cvd.snapshot()

@app.post("/api/v1/outcomes/evaluate")
async def outcomes_evaluate():
    try:
        return await evaluate_active_once()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Outcome evaluation unavailable: {exc}") from exc


@app.get("/api/v1/dashboard")
async def dashboard():
    try:
        return await build_dashboard()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Dashboard unavailable: {exc}") from exc

@app.get("/api/v1/backtest")
async def backtest(
    interval: str = Query(default="15"),
    candles: int = Query(default=1000, ge=200, le=1000),
):
    try:
        rows = await get_kline_history(interval=interval, limit=candles)
        trades, max_dd = run_backtest(rows)
        stats = summarize(trades, max_dd)
        return {
            "strategy_version": settings.strategy_version,
            "symbol": settings.symbol,
            "interval": interval,
            "candles": len(rows),
            "assumptions": {
                "round_trip_fee_bps": settings.backtest_fee_bps_round_trip,
                "round_trip_slippage_bps": settings.backtest_slippage_bps_round_trip,
                "target_r": 1.5,
                "max_hold_bars": 4,
                "same_bar_stop_target_rule": "STOP_FIRST",
            },
            "stats": stats,
            "recent_trades": [t.__dict__ for t in trades[-20:]],
        }
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Backtest unavailable: {exc}") from exc

@app.get("/api/v1/validation/walk-forward")
async def validation_walk_forward(
    interval: str = Query(default="15"),
    candles: int = Query(default=1000, ge=300, le=1000),
):
    try:
        rows = await get_kline_history(interval=interval, limit=candles)
        result = walk_forward(rows)
        result["strategy_version"] = settings.strategy_version
        result["symbol"] = settings.symbol
        result["interval"] = interval
        return result
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Validation unavailable: {exc}") from exc
