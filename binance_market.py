import asyncio
import httpx
from app.config import settings

def _f(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default

def _map_kline(row):
    # Binance futures:
    # openTime, open, high, low, close, volume, closeTime, quoteVolume, ...
    return [
        str(row[0]),
        str(row[1]),
        str(row[2]),
        str(row[3]),
        str(row[4]),
        str(row[5]),
        str(row[7] if len(row) > 7 else 0),
    ]

async def _get(client, path, params=None):
    r = await client.get(path, params=params or {})
    r.raise_for_status()
    return r.json()

async def fetch_binance_bundle():
    timeout = httpx.Timeout(12.0, connect=5.0)
    async with httpx.AsyncClient(
        base_url=settings.binance_futures_base_url,
        timeout=timeout,
        headers={"User-Agent": "AMP-TRADE-FIND/0.8.1"},
    ) as client:
        k5, k15, k60, book, ticker24, premium, oi_now, oi_hist, trades, depth = await asyncio.gather(
            _get(client, "/fapi/v1/klines", {"symbol": settings.symbol, "interval": "5m", "limit": 200}),
            _get(client, "/fapi/v1/klines", {"symbol": settings.symbol, "interval": "15m", "limit": 200}),
            _get(client, "/fapi/v1/klines", {"symbol": settings.symbol, "interval": "1h", "limit": 200}),
            _get(client, "/fapi/v1/ticker/bookTicker", {"symbol": settings.symbol}),
            _get(client, "/fapi/v1/ticker/24hr", {"symbol": settings.symbol}),
            _get(client, "/fapi/v1/premiumIndex", {"symbol": settings.symbol}),
            _get(client, "/fapi/v1/openInterest", {"symbol": settings.symbol}),
            _get(client, "/futures/data/openInterestHist", {"symbol": settings.symbol, "period": "5m", "limit": 3}),
            _get(client, "/fapi/v1/aggTrades", {"symbol": settings.symbol, "limit": 1000}),
            _get(client, "/fapi/v1/depth", {"symbol": settings.symbol, "limit": 200}),
        )

    buy = sell = 0.0
    for t in trades:
        qty = _f(t.get("q"))
        # m=True means buyer is maker, so aggressive taker is SELL.
        if bool(t.get("m")):
            sell += qty
        else:
            buy += qty

    total = buy + sell
    delta = buy - sell
    delta_pct = (delta / total * 100.0) if total else 0.0

    bid_depth = sum(_f(x[1]) for x in depth.get("bids", []))
    ask_depth = sum(_f(x[1]) for x in depth.get("asks", []))
    depth_total = bid_depth + ask_depth
    imbalance = ((bid_depth - ask_depth) / depth_total) if depth_total else 0.0

    hist = sorted(oi_hist, key=lambda x: int(x.get("timestamp", 0) or 0))
    oi_current_hist = _f(hist[-1].get("sumOpenInterest")) if hist else None
    oi_prev_hist = _f(hist[-2].get("sumOpenInterest")) if len(hist) >= 2 else None
    oi_change_pct = None
    if oi_current_hist is not None and oi_prev_hist not in (None, 0):
        oi_change_pct = (oi_current_hist - oi_prev_hist) / oi_prev_hist * 100.0

    last_price = _f(ticker24.get("lastPrice"))
    bid = _f(book.get("bidPrice"))
    ask = _f(book.get("askPrice"))

    return {
        "source": "BINANCE",
        "5": [_map_kline(x) for x in k5],
        "15": [_map_kline(x) for x in k15],
        "60": [_map_kline(x) for x in k60],
        "ticker": {
            "lastPrice": str(last_price),
            "bid1Price": str(bid),
            "ask1Price": str(ask),
            "fundingRate": str(premium.get("lastFundingRate", "")),
            "openInterest": str(oi_now.get("openInterest", "")),
            "price24hPcnt": str(_f(ticker24.get("priceChangePercent")) / 100.0),
        },
        "orderflow": {
            "trade_count": len(trades),
            "buy_volume_btc": round(buy, 4),
            "sell_volume_btc": round(sell, 4),
            "taker_delta_btc": round(delta, 4),
            "taker_delta_pct": round(delta_pct, 3),
            "cvd_btc": round(delta, 4),
            "orderbook_bid_btc": round(bid_depth, 4),
            "orderbook_ask_btc": round(ask_depth, 4),
            "orderbook_imbalance": round(imbalance, 4),
            "oi_current_btc": round(oi_current_hist, 4) if oi_current_hist is not None else None,
            "oi_5m_ago_btc": round(oi_prev_hist, 4) if oi_prev_hist is not None else None,
            "oi_change_pct": round(oi_change_pct, 4) if oi_change_pct is not None else None,
        },
    }

async def fetch_binance_last_price():
    timeout = httpx.Timeout(8.0, connect=4.0)
    async with httpx.AsyncClient(base_url=settings.binance_futures_base_url, timeout=timeout) as client:
        data = await _get(client, "/fapi/v1/ticker/price", {"symbol": settings.symbol})
    return float(data["price"])

async def get_binance_kline_history(interval="15", limit=1000, end_ms=None):
    mapping = {"5": "5m", "15": "15m", "60": "1h", "240": "4h", "D": "1d"}
    binance_interval = mapping.get(str(interval), str(interval) if str(interval).endswith(("m","h","d")) else "15m")
    params = {"symbol": settings.symbol, "interval": binance_interval, "limit": min(max(int(limit), 1), 1000)}
    if end_ms is not None:
        params["endTime"] = int(end_ms)
    timeout = httpx.Timeout(12.0, connect=5.0)
    async with httpx.AsyncClient(base_url=settings.binance_futures_base_url, timeout=timeout) as client:
        data = await _get(client, "/fapi/v1/klines", params)
    return [_map_kline(x) for x in data]
