from app.services.bybit import fetch_market_bundle, fetch_last_price, get_kline_history
from app.services.binance_market import fetch_binance_bundle, fetch_binance_last_price, get_binance_kline_history
from app.services.okx_market import fetch_okx_bundle, fetch_okx_last_price, get_okx_kline_history
from app.services.kraken_market import fetch_kraken_bundle, fetch_kraken_last_price, get_kraken_kline_history
from app.services.coinbase_market import fetch_coinbase_bundle, fetch_coinbase_last_price, get_coinbase_kline_history
B=[("BYBIT",fetch_market_bundle),("BINANCE",fetch_binance_bundle),("OKX",fetch_okx_bundle),("KRAKEN",fetch_kraken_bundle),("COINBASE",fetch_coinbase_bundle)]
P=[("BYBIT",fetch_last_price),("BINANCE",fetch_binance_last_price),("OKX",fetch_okx_last_price),("KRAKEN",fetch_kraken_last_price),("COINBASE",fetch_coinbase_last_price)]
H=[("BYBIT",get_kline_history),("BINANCE",get_binance_kline_history),("OKX",get_okx_kline_history),("KRAKEN",get_kraken_kline_history),("COINBASE",get_coinbase_kline_history)]
async def fetch_market_bundle_resilient():
    errors={}
    for name,fn in B:
        try:
            x=await fn(); x["source"]=name; x["source_errors"]=errors; return x
        except Exception as e: errors[name]=str(e)[:300]
    raise RuntimeError(f"All market-data sources unavailable: {errors}")
async def fetch_last_price_resilient():
    errors={}
    for name,fn in P:
        try: return await fn()
        except Exception as e: errors[name]=str(e)[:200]
    raise RuntimeError(f"All price sources unavailable: {errors}")
async def get_kline_history_resilient(interval="15",limit=1000,end_ms=None):
    errors={}
    for name,fn in H:
        try:
            rows=await fn(interval=interval,limit=limit,end_ms=end_ms)
            if len(rows)>=60: return rows
            errors[name]=f"Only {len(rows)} candles"
        except Exception as e: errors[name]=str(e)[:200]
    raise RuntimeError(f"All historical candle sources unavailable: {errors}")
