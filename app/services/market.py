from app.config import settings
from app.services.bybit import fetch_market_bundle
from app.services.indicators import build_indicators
from app.services.orderflow import build_orderflow
from app.services.cross_exchange import build_cross_exchange
from app.services.live_cvd import live_cvd
from app.services.event_risk import event_risk

async def build_market_snapshot() -> dict:
    bundle = await fetch_market_bundle()
    ticker = bundle["ticker"]

    bid = float(ticker.get("bid1Price") or 0)
    ask = float(ticker.get("ask1Price") or 0)
    price = float(ticker["lastPrice"])
    midpoint = (bid + ask) / 2 if bid and ask else price
    spread_bps = ((ask - bid) / midpoint * 10000) if bid and ask and midpoint else 0.0

    funding = ticker.get("fundingRate")
    oi = ticker.get("openInterest")
    chg = ticker.get("price24hPcnt")

    orderflow = build_orderflow(bundle["trades"], bundle["orderbook"], bundle["oi"])
    cross_exchange = await build_cross_exchange(orderflow)

    return {
        "symbol": settings.symbol,
        "price": round(price, 2),
        "bid": round(bid, 2),
        "ask": round(ask, 2),
        "spread_bps": round(spread_bps, 3),
        "funding_rate": float(funding) if funding not in (None, "") else None,
        "open_interest": float(oi) if oi not in (None, "") else None,
        "change_24h_pct": round(float(chg) * 100, 3) if chg not in (None, "") else None,
        "tf_5m": build_indicators(bundle["5"], "5m"),
        "tf_15m": build_indicators(bundle["15"], "15m"),
        "tf_1h": build_indicators(bundle["60"], "1h"),
        "orderflow": orderflow,
        "cross_exchange": cross_exchange,
        "live_cvd": live_cvd.snapshot(),
        "event_risk": event_risk(),
    }
