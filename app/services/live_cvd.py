import asyncio
import json
import time
from collections import deque
from dataclasses import dataclass
import websockets

from app.config import settings

@dataclass
class TradePoint:
    ts_ms: int
    signed_volume: float
    price: float

class LiveCVD:
    def __init__(self):
        self.trades = deque()
        self.connected = False
        self.last_message_ms = 0
        self.last_error = None
        self.total_messages = 0

    def add(self, ts_ms: int, side: str, volume: float, price: float):
        signed = volume if side.lower() == "buy" else -volume
        self.trades.append(TradePoint(ts_ms, signed, price))
        self.last_message_ms = int(time.time() * 1000)
        self._trim()

    def _trim(self):
        cutoff = int(time.time() * 1000) - (20 * 60 * 1000)
        while self.trades and self.trades[0].ts_ms < cutoff:
            self.trades.popleft()

    def _window(self, minutes: int):
        cutoff = int(time.time() * 1000) - minutes * 60 * 1000
        vals = [x for x in self.trades if x.ts_ms >= cutoff]
        cvd = sum(x.signed_volume for x in vals)
        buy = sum(x.signed_volume for x in vals if x.signed_volume > 0)
        sell = -sum(x.signed_volume for x in vals if x.signed_volume < 0)
        total = buy + sell
        delta_pct = (cvd / total * 100.0) if total else 0.0
        return {
            "minutes": minutes,
            "trade_count": len(vals),
            "buy_volume_btc": round(buy, 4),
            "sell_volume_btc": round(sell, 4),
            "cvd_btc": round(cvd, 4),
            "delta_pct": round(delta_pct, 3),
        }

    def snapshot(self):
        self._trim()
        age_ms = int(time.time() * 1000) - self.last_message_ms if self.last_message_ms else None
        return {
            "connected": self.connected,
            "last_message_age_ms": age_ms,
            "buffered_trades": len(self.trades),
            "total_messages": self.total_messages,
            "last_error": self.last_error,
            "cvd_1m": self._window(1),
            "cvd_5m": self._window(5),
            "cvd_15m": self._window(15),
        }

live_cvd = LiveCVD()

async def run_bybit_trade_stream():
    topic = f"publicTrade.{settings.symbol}"
    subscribe = {"op": "subscribe", "args": [topic]}

    while True:
        try:
            async with websockets.connect(
                settings.bybit_ws_linear_url,
                ping_interval=None,
                close_timeout=5,
                max_queue=4096,
            ) as ws:
                await ws.send(json.dumps(subscribe))
                live_cvd.connected = True
                live_cvd.last_error = None

                async def heartbeat():
                    while True:
                        await asyncio.sleep(20)
                        await ws.send(json.dumps({"op": "ping"}))

                hb = asyncio.create_task(heartbeat())
                try:
                    async for raw in ws:
                        msg = json.loads(raw)
                        if msg.get("topic") != topic:
                            continue
                        live_cvd.total_messages += 1
                        for t in msg.get("data", []):
                            live_cvd.add(
                                int(t.get("T", 0)),
                                str(t.get("S", "")),
                                float(t.get("v", 0)),
                                float(t.get("p", 0)),
                            )
                finally:
                    hb.cancel()
                    live_cvd.connected = False
        except asyncio.CancelledError:
            live_cvd.connected = False
            raise
        except Exception as exc:
            live_cvd.connected = False
            live_cvd.last_error = str(exc)[:240]
            await asyncio.sleep(3)
