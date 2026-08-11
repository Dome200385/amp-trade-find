import asyncio
import httpx
from app.config import settings

def _f(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default

def _granularity(interval):
    m = {"5": 300, "15": 900, "60": 3600, "240": 14400, "D": 86400}
    return m.get(str(interval), 900)

def _map_candles(rows):
    # Coinbase Exchange candle: [time, low, high, open, close, volume]
    # API returns newest-first; indicators need oldest-first.
    out = []
    for x in reversed(rows):
        out.append([
            str(int(x[0]) * 1000),
            str(x[3]), str(x[2]), str(x[1]), str(x[4]), str(x[5]), "0"
        ])
    return out

async def _get(client, path, params=None):
    r = await client.get(path, params=params or {})
    r.raise_for_status()
    return r.json()

async def fetch_coinbase_bundle():
    timeout = httpx.Timeout(12.0, connect=5.0)
    headers = {"User-Agent": "AMP-TRADE-FIND/0.8.1"}
    base = settings.coinbase_exchange_base_url
    product = settings.coinbase_product

    async with httpx.AsyncClient(base_url=base, timeout=timeout, headers=headers) as client:
        c5, c15, c60, ticker, trades, book = await asyncio.gather(
            _get(client, f"/products/{product}/candles", {"granularity": 300}),
            _get(client, f"/products/{product}/candles", {"granularity": 900}),
            _get(client, f"/products/{product}/candles", {"granularity": 3600}),
            _get(client, f"/products/{product}/ticker"),
            _get(client, f"/products/{product}/trades"),
            _get(client, f"/products/{product}/book", {"level": 2}),
        )

    buy = sell = 0.0
    for t in trades:
        qty = _f(t.get("size"))
        maker_side = str(t.get("side", "")).lower()
        if maker_side == "sell":
            buy += qty
        elif maker_side == "buy":
            sell += qty

    total = buy + sell
    delta = buy - sell
    delta_pct = delta / total * 100.0 if total else 0.0

    bid_depth = sum(_f(x[1]) for x in book.get("bids", []))
    ask_depth = sum(_f(x[1]) for x in book.get("asks", []))
    depth_total = bid_depth + ask_depth
    imbalance = (bid_depth - ask_depth) / depth_total if depth_total else 0.0

    price = _f(ticker.get("price"))
    bid = _f(ticker.get("bid"))
    ask = _f(ticker.get("ask"))

    return {
        "source": "COINBASE",
        "5": _map_candles(c5),
        "15": _map_candles(c15),
        "60": _map_candles(c60),
        "ticker": {
            "lastPrice": str(price),
            "bid1Price": str(bid),
            "ask1Price": str(ask),
            "fundingRate": "",
            "openInterest": "",
            "price24hPcnt": "",
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
            "oi_current_btc": None,
            "oi_5m_ago_btc": None,
            "oi_change_pct": None,
        },
    }

async def fetch_coinbase_last_price():
    timeout = httpx.Timeout(8.0, connect=4.0)
    headers = {"User-Agent": "AMP-TRADE-FIND/0.8.1"}
    async with httpx.AsyncClient(base_url=settings.coinbase_exchange_base_url, timeout=timeout, headers=headers) as client:
        data = await _get(client, f"/products/{settings.coinbase_product}/ticker")
    return float(data["price"])

async def get_coinbase_kline_history(interval="15", limit=300, end_ms=None):
    # Coinbase Exchange returns max ~300 candles, sufficient as last fallback.
    params = {"granularity": _granularity(interval)}
    timeout = httpx.Timeout(12.0, connect=5.0)
    headers = {"User-Agent": "AMP-TRADE-FIND/0.8.1"}
    async with httpx.AsyncClient(base_url=settings.coinbase_exchange_base_url, timeout=timeout, headers=headers) as client:
        data = await _get(client, f"/products/{settings.coinbase_product}/candles", params)
    return _map_candles(data)[-min(int(limit), 300):]
