import asyncio
import httpx
from app.config import settings

def _f(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default

def _venue_error(name: str, market_type: str, error) -> dict:
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

def _venue_from_primary(name: str, market_type: str, orderflow: dict) -> dict:
    return {
        "venue": name,
        "market_type": market_type,
        "trade_count": orderflow["trade_count"],
        "buy_volume_btc": orderflow["buy_volume_btc"],
        "sell_volume_btc": orderflow["sell_volume_btc"],
        "taker_delta_btc": orderflow["taker_delta_btc"],
        "taker_delta_pct": orderflow["taker_delta_pct"],
        "orderbook_imbalance": orderflow["orderbook_imbalance"],
        "available": True,
        "error": None,
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
            trades, book = trades_r.json(), book_r.json()

        buy = sell = 0.0
        for t in trades:
            qty = _f(t.get("q"))
            if bool(t.get("m")): sell += qty
            else: buy += qty
        total = buy + sell
        delta = buy - sell
        bid_depth = sum(_f(x[1]) for x in book.get("bids", []))
        ask_depth = sum(_f(x[1]) for x in book.get("asks", []))
        dt = bid_depth + ask_depth
        return {
            "venue": "BINANCE", "market_type": "FUTURES", "trade_count": len(trades),
            "buy_volume_btc": round(buy,4), "sell_volume_btc": round(sell,4),
            "taker_delta_btc": round(delta,4),
            "taker_delta_pct": round(delta/total*100 if total else 0,3),
            "orderbook_imbalance": round((bid_depth-ask_depth)/dt if dt else 0,4),
            "available": True, "error": None,
        }
    except Exception as exc:
        return _venue_error("BINANCE", "FUTURES", exc)

async def _coinbase() -> dict:
    try:
        timeout = httpx.Timeout(8.0, connect=4.0)
        headers = {"User-Agent": "AMP-TRADE-FIND/0.8.1"}
        async with httpx.AsyncClient(base_url=settings.coinbase_exchange_base_url, timeout=timeout, headers=headers) as client:
            trades_r, book_r = await asyncio.gather(
                client.get(f"/products/{settings.coinbase_product}/trades"),
                client.get(f"/products/{settings.coinbase_product}/book", params={"level": 2}),
            )
            trades_r.raise_for_status()
            book_r.raise_for_status()
            trades, book = trades_r.json(), book_r.json()

        buy = sell = 0.0
        for t in trades:
            qty = _f(t.get("size"))
            maker = str(t.get("side","")).lower()
            if maker == "sell": buy += qty
            elif maker == "buy": sell += qty
        total = buy + sell
        delta = buy - sell
        bid_depth = sum(_f(x[1]) for x in book.get("bids", []))
        ask_depth = sum(_f(x[1]) for x in book.get("asks", []))
        dt = bid_depth + ask_depth
        return {
            "venue": "COINBASE", "market_type": "SPOT", "trade_count": len(trades),
            "buy_volume_btc": round(buy,4), "sell_volume_btc": round(sell,4),
            "taker_delta_btc": round(delta,4),
            "taker_delta_pct": round(delta/total*100 if total else 0,3),
            "orderbook_imbalance": round((bid_depth-ask_depth)/dt if dt else 0,4),
            "available": True, "error": None,
        }
    except Exception as exc:
        return _venue_error("COINBASE", "SPOT", exc)

async def build_cross_exchange(orderflow: dict, primary_source: str = "BYBIT", source_errors: dict | None = None) -> dict:
    source_errors = source_errors or {}

    if primary_source == "BYBIT":
        bybit = _venue_from_primary("BYBIT", "FUTURES", orderflow)
        binance, coinbase = await asyncio.gather(_binance(), _coinbase())
    elif primary_source == "BINANCE":
        bybit = _venue_error("BYBIT", "FUTURES", source_errors.get("BYBIT", "Bybit REST unavailable"))
        binance = _venue_from_primary("BINANCE", "FUTURES", orderflow)
        coinbase = await _coinbase()
    else:
        bybit = _venue_error("BYBIT", "FUTURES", source_errors.get("BYBIT", "Bybit REST unavailable"))
        binance = await _binance()
        coinbase = _venue_from_primary("COINBASE", "SPOT", orderflow)

    venues = [bybit, binance, coinbase]
    available = [v for v in venues if v["available"]]

    long_conf = sum(1 for v in available if v["taker_delta_pct"] >= 5 and
                    (v["orderbook_imbalance"] is None or v["orderbook_imbalance"] >= 0.03))
    short_conf = sum(1 for v in available if v["taker_delta_pct"] <= -5 and
                     (v["orderbook_imbalance"] is None or v["orderbook_imbalance"] <= -0.03))

    n = len(available)
    if n and long_conf >= 2 and long_conf > short_conf:
        consensus, strength = "LONG", long_conf / n
    elif n and short_conf >= 2 and short_conf > long_conf:
        consensus, strength = "SHORT", short_conf / n
    elif long_conf and short_conf:
        consensus, strength = "MIXED", max(long_conf, short_conf) / n
    else:
        consensus, strength = "NEUTRAL", 0.0

    return {
        "bybit": bybit, "binance": binance, "coinbase": coinbase,
        "long_confirmations": long_conf, "short_confirmations": short_conf,
        "available_venues": n, "consensus": consensus,
        "consensus_strength": round(strength, 3),
    }
