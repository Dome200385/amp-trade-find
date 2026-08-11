import asyncio
import httpx
from app.config import settings

def _f(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default

def _venue_error(name: str, market_type: str, error: Exception) -> dict:
    return {
        "venue": name,
        "market_type": market_type,
        "trade_count": 0,
        "buy_volume_btc": 0.0,
        "sell_volume_btc": 0.0,
        "taker_delta_btc": 0.0,
        "taker_delta_pct": 0.0,
        "orderbook_imbalance": None,
        "available": False,
        "error": str(error)[:240],
    }

async def _binance() -> dict:
    try:
        timeout = httpx.Timeout(8.0, connect=4.0)
        async with httpx.AsyncClient(base_url=settings.binance_futures_base_url, timeout=timeout) as client:
            trades_r, book_r = await asyncio.gather(
                client.get("/fapi/v1/aggTrades", params={"symbol": settings.symbol, "limit": 1000}),
                client.get("/fapi/v1/depth", params={"symbol": settings.symbol, "limit": 100}),
            )
            trades_r.raise_for_status()
            book_r.raise_for_status()
            trades = trades_r.json()
            book = book_r.json()

        buy = sell = 0.0
        for t in trades:
            qty = _f(t.get("q"))
            # Binance `m` = buyer is maker. If buyer is maker, aggressive taker is SELL.
            if bool(t.get("m")):
                sell += qty
            else:
                buy += qty

        total = buy + sell
        delta = buy - sell
        delta_pct = delta / total * 100 if total else 0.0

        bid_depth = sum(_f(x[1]) for x in book.get("bids", []))
        ask_depth = sum(_f(x[1]) for x in book.get("asks", []))
        depth_total = bid_depth + ask_depth
        imbalance = (bid_depth - ask_depth) / depth_total if depth_total else 0.0

        return {
            "venue": "BINANCE",
            "market_type": "FUTURES",
            "trade_count": len(trades),
            "buy_volume_btc": round(buy, 4),
            "sell_volume_btc": round(sell, 4),
            "taker_delta_btc": round(delta, 4),
            "taker_delta_pct": round(delta_pct, 3),
            "orderbook_imbalance": round(imbalance, 4),
            "available": True,
            "error": None,
        }
    except Exception as exc:
        return _venue_error("BINANCE", "FUTURES", exc)

async def _coinbase() -> dict:
    try:
        timeout = httpx.Timeout(8.0, connect=4.0)
        headers = {"User-Agent": "AMP-TRADE-FIND/0.3"}
        async with httpx.AsyncClient(
            base_url=settings.coinbase_exchange_base_url,
            timeout=timeout,
            headers=headers,
        ) as client:
            trades_r, book_r = await asyncio.gather(
                client.get(f"/products/{settings.coinbase_product}/trades", params={"limit": 1000}),
                client.get(f"/products/{settings.coinbase_product}/book", params={"level": 2}),
            )
            trades_r.raise_for_status()
            book_r.raise_for_status()
            trades = trades_r.json()
            book = book_r.json()

        buy = sell = 0.0
        for t in trades:
            qty = _f(t.get("size"))
            maker_side = str(t.get("side", "")).lower()
            # Coinbase Exchange documents `side` as maker side.
            # maker SELL => aggressive taker BUY; maker BUY => aggressive taker SELL.
            if maker_side == "sell":
                buy += qty
            elif maker_side == "buy":
                sell += qty

        total = buy + sell
        delta = buy - sell
        delta_pct = delta / total * 100 if total else 0.0

        bid_depth = sum(_f(x[1]) for x in book.get("bids", []))
        ask_depth = sum(_f(x[1]) for x in book.get("asks", []))
        depth_total = bid_depth + ask_depth
        imbalance = (bid_depth - ask_depth) / depth_total if depth_total else 0.0

        return {
            "venue": "COINBASE",
            "market_type": "SPOT",
            "trade_count": len(trades),
            "buy_volume_btc": round(buy, 4),
            "sell_volume_btc": round(sell, 4),
            "taker_delta_btc": round(delta, 4),
            "taker_delta_pct": round(delta_pct, 3),
            "orderbook_imbalance": round(imbalance, 4),
            "available": True,
            "error": None,
        }
    except Exception as exc:
        return _venue_error("COINBASE", "SPOT", exc)

def _bybit_venue(orderflow: dict) -> dict:
    return {
        "venue": "BYBIT",
        "market_type": "FUTURES",
        "trade_count": orderflow["trade_count"],
        "buy_volume_btc": orderflow["buy_volume_btc"],
        "sell_volume_btc": orderflow["sell_volume_btc"],
        "taker_delta_btc": orderflow["taker_delta_btc"],
        "taker_delta_pct": orderflow["taker_delta_pct"],
        "orderbook_imbalance": orderflow["orderbook_imbalance"],
        "available": True,
        "error": None,
    }

async def build_cross_exchange(orderflow: dict) -> dict:
    bybit = _bybit_venue(orderflow)
    binance, coinbase = await asyncio.gather(_binance(), _coinbase())
    venues = [bybit, binance, coinbase]
    available = [v for v in venues if v["available"]]

    long_conf = sum(
        1 for v in available
        if v["taker_delta_pct"] >= 5 and (v["orderbook_imbalance"] is None or v["orderbook_imbalance"] >= 0.03)
    )
    short_conf = sum(
        1 for v in available
        if v["taker_delta_pct"] <= -5 and (v["orderbook_imbalance"] is None or v["orderbook_imbalance"] <= -0.03)
    )

    n = len(available)
    if n and long_conf >= 2 and long_conf > short_conf:
        consensus = "LONG"
        strength = long_conf / n
    elif n and short_conf >= 2 and short_conf > long_conf:
        consensus = "SHORT"
        strength = short_conf / n
    elif long_conf and short_conf:
        consensus = "MIXED"
        strength = max(long_conf, short_conf) / n if n else 0.0
    else:
        consensus = "NEUTRAL"
        strength = 0.0

    return {
        "bybit": bybit,
        "binance": binance,
        "coinbase": coinbase,
        "long_confirmations": long_conf,
        "short_confirmations": short_conf,
        "available_venues": n,
        "consensus": consensus,
        "consensus_strength": round(strength, 3),
    }
