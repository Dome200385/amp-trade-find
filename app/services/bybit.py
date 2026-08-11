import asyncio
import httpx
from app.config import settings

class BybitError(RuntimeError):
    pass

async def _get(client: httpx.AsyncClient, path: str, params: dict) -> dict:
    r = await client.get(path, params=params)
    r.raise_for_status()
    payload = r.json()
    if payload.get("retCode") != 0:
        raise BybitError(f"Bybit error {payload.get('retCode')}: {payload.get('retMsg')}")
    return payload["result"]

async def get_kline(client: httpx.AsyncClient, interval: str, limit: int = 200) -> list[list[str]]:
    result = await _get(
        client, "/v5/market/kline",
        {"category": settings.category, "symbol": settings.symbol, "interval": interval, "limit": limit},
    )
    return list(reversed(result["list"]))

async def get_ticker(client: httpx.AsyncClient) -> dict:
    result = await _get(
        client, "/v5/market/tickers",
        {"category": settings.category, "symbol": settings.symbol},
    )
    return result["list"][0]

async def get_recent_trades(client: httpx.AsyncClient, limit: int = 1000) -> list[dict]:
    result = await _get(
        client, "/v5/market/recent-trade",
        {"category": settings.category, "symbol": settings.symbol, "limit": limit},
    )
    return result["list"]

async def get_orderbook(client: httpx.AsyncClient, limit: int = 200) -> dict:
    return await _get(
        client, "/v5/market/orderbook",
        {"category": settings.category, "symbol": settings.symbol, "limit": limit},
    )

async def get_open_interest(client: httpx.AsyncClient, interval: str = "5min", limit: int = 12) -> list[dict]:
    result = await _get(
        client, "/v5/market/open-interest",
        {
            "category": settings.category,
            "symbol": settings.symbol,
            "intervalTime": interval,
            "limit": limit,
        },
    )
    return result["list"]

async def fetch_market_bundle() -> dict:
    timeout = httpx.Timeout(12.0, connect=5.0)
    async with httpx.AsyncClient(
        base_url=settings.bybit_base_url,
        timeout=timeout,
        headers={"User-Agent": "AMP-TRADE-FIND/0.2"},
    ) as client:
        k5, k15, k60, ticker, trades, orderbook, oi = await asyncio.gather(
            get_kline(client, "5"),
            get_kline(client, "15"),
            get_kline(client, "60"),
            get_ticker(client),
            get_recent_trades(client),
            get_orderbook(client),
            get_open_interest(client),
        )
    return {
        "5": k5,
        "15": k15,
        "60": k60,
        "ticker": ticker,
        "trades": trades,
        "orderbook": orderbook,
        "oi": oi,
    }


async def fetch_last_price() -> float:
    timeout = httpx.Timeout(8.0, connect=4.0)
    async with httpx.AsyncClient(
        base_url=settings.bybit_base_url,
        timeout=timeout,
        headers={"User-Agent": "AMP-TRADE-FIND/0.4"},
    ) as client:
        ticker = await get_ticker(client)
    return float(ticker["lastPrice"])


async def get_kline_history(interval: str = "15", limit: int = 1000, end_ms: int | None = None) -> list[list[str]]:
    timeout = httpx.Timeout(12.0, connect=5.0)
    params = {
        "category": settings.category,
        "symbol": settings.symbol,
        "interval": interval,
        "limit": min(max(int(limit), 1), 1000),
    }
    if end_ms is not None:
        params["end"] = int(end_ms)
    async with httpx.AsyncClient(
        base_url=settings.bybit_base_url,
        timeout=timeout,
        headers={"User-Agent": "AMP-TRADE-FIND/0.5"},
    ) as client:
        result = await _get(client, "/v5/market/kline", params)
    return list(reversed(result["list"]))
