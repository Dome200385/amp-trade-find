from app.services.signal_quality import build_signal_quality

def v(name, typ, delta, imbalance, available=True):
    return {
        "venue": name, "market_type": typ, "available": available,
        "taker_delta_pct": delta, "orderbook_imbalance": imbalance,
    }

def base(bybit=None, binance=None, okx=None, kraken=None, coinbase=None, consensus="NEUTRAL"):
    return {
        "bybit": bybit or v("BYBIT","FUTURES",0,0,False),
        "binance": binance or v("BINANCE","FUTURES",0,0,False),
        "okx": okx or v("OKX","SWAP",0,0,False),
        "kraken": kraken or v("KRAKEN","SPOT",0,0,False),
        "coinbase": coinbase or v("COINBASE","SPOT",0,0,False),
        "consensus": consensus,
        "available_venues": sum(bool(x.get("available")) for x in [
            bybit or {}, binance or {}, okx or {}, kraken or {}, coinbase or {}
        ]),
    }

def live(delta=10):
    return {"connected": True, "cvd_5m": {"trade_count": 100, "delta_pct": delta}}

def test_high_quality_long_requires_spot_and_derivative():
    x = base(
        okx=v("OKX","SWAP",12,0.20),
        kraken=v("KRAKEN","SPOT",8,0.10),
        coinbase=v("COINBASE","SPOT",7,0.20),
        consensus="LONG",
    )
    q = build_signal_quality(x, live(9))
    assert q["grade"] == "HIGH"
    assert q["cross_market_long"] is True

def test_conflict_is_low_quality():
    x = base(
        okx=v("OKX","SWAP",-15,-0.20),
        kraken=v("KRAKEN","SPOT",-8,-0.10),
        coinbase=v("COINBASE","SPOT",14,0.30),
        consensus="MIXED",
    )
    q = build_signal_quality(x, live(12))
    assert q["market_conflict"] is True
    assert q["grade"] == "LOW"
