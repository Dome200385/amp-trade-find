from app.services.bybit import fetch_market_bundle, fetch_last_price, get_kline_history
from app.services.binance_market import fetch_binance_bundle, fetch_binance_last_price, get_binance_kline_history
from app.services.coinbase_market import fetch_coinbase_bundle, fetch_coinbase_last_price, get_coinbase_kline_history

async def fetch_market_bundle_resilient():
    errors = {}
    try:
        b = await fetch_market_bundle()
        b["source"] = "BYBIT"
        b["source_errors"] = errors
        return b
    except Exception as exc:
        errors["BYBIT"] = str(exc)[:300]

    try:
        b = await fetch_binance_bundle()
        b["source_errors"] = errors
        return b
    except Exception as exc:
        errors["BINANCE"] = str(exc)[:300]

    try:
        b = await fetch_coinbase_bundle()
        b["source_errors"] = errors
        return b
    except Exception as exc:
        errors["COINBASE"] = str(exc)[:300]

    raise RuntimeError(f"All market-data sources unavailable: {errors}")

async def fetch_last_price_resilient():
    errors = {}
    for name, fn in [
        ("BYBIT", fetch_last_price),
        ("BINANCE", fetch_binance_last_price),
        ("COINBASE", fetch_coinbase_last_price),
    ]:
        try:
            return await fn()
        except Exception as exc:
            errors[name] = str(exc)[:200]
    raise RuntimeError(f"All price sources unavailable: {errors}")

async def get_kline_history_resilient(interval="15", limit=1000, end_ms=None):
    errors = {}
    for name, fn in [
        ("BYBIT", get_kline_history),
        ("BINANCE", get_binance_kline_history),
        ("COINBASE", get_coinbase_kline_history),
    ]:
        try:
            rows = await fn(interval=interval, limit=limit, end_ms=end_ms)
            if len(rows) >= 60:
                return rows
            errors[name] = f"Only {len(rows)} candles"
        except Exception as exc:
            errors[name] = str(exc)[:200]
    raise RuntimeError(f"All historical candle sources unavailable: {errors}")
