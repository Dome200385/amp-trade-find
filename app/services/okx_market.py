import asyncio
import httpx
from app.config import settings

def _f(v,d=0.0):
    try: return float(v)
    except (TypeError,ValueError): return d

async def _get(c,path,params=None):
    r=await c.get(path,params=params or {}); r.raise_for_status(); j=r.json()
    if str(j.get("code","0"))!="0": raise RuntimeError(f"OKX {j.get('code')}: {j.get('msg')}")
    return j.get("data",[])

def _candles(rows):
    return [[str(x[0]),str(x[1]),str(x[2]),str(x[3]),str(x[4]),str(x[5]),str(x[7] if len(x)>7 else 0)] for x in reversed(rows)]

async def fetch_okx_bundle():
    inst=settings.okx_instrument
    async with httpx.AsyncClient(base_url=settings.okx_base_url,timeout=12.0,headers={"User-Agent":"AMP-TRADE-FIND/0.8.2"}) as c:
        c5,c15,c60,ticker,trades,books,oi,funding=await asyncio.gather(
            _get(c,"/api/v5/market/candles",{"instId":inst,"bar":"5m","limit":200}),
            _get(c,"/api/v5/market/candles",{"instId":inst,"bar":"15m","limit":200}),
            _get(c,"/api/v5/market/candles",{"instId":inst,"bar":"1H","limit":200}),
            _get(c,"/api/v5/market/ticker",{"instId":inst}),
            _get(c,"/api/v5/market/trades",{"instId":inst,"limit":500}),
            _get(c,"/api/v5/market/books",{"instId":inst,"sz":200}),
            _get(c,"/api/v5/public/open-interest",{"instType":"SWAP","instId":inst}),
            _get(c,"/api/v5/public/funding-rate",{"instId":inst}))
    t=ticker[0] if ticker else {}; buy=sell=0.0
    for tr in trades:
        q=_f(tr.get("sz")); side=tr.get("side")
        if side=="buy": buy+=q
        elif side=="sell": sell+=q
    total=buy+sell; delta=buy-sell; b=books[0] if books else {}
    bid_depth=sum(_f(x[1]) for x in b.get("bids",[])); ask_depth=sum(_f(x[1]) for x in b.get("asks",[])); depth=bid_depth+ask_depth
    oi_now=_f(oi[0].get("oi")) if oi else None; fund=funding[0].get("fundingRate") if funding else None
    last=_f(t.get("last")); op=_f(t.get("open24h")); pct=(last-op)/op if op else None
    return {"source":"OKX","5":_candles(c5),"15":_candles(c15),"60":_candles(c60),
      "ticker":{"lastPrice":str(last),"bid1Price":str(_f(t.get("bidPx"))),"ask1Price":str(_f(t.get("askPx"))),"fundingRate":str(fund or ""),"openInterest":str(oi_now or ""),"price24hPcnt":str(pct) if pct is not None else ""},
      "orderflow":{"trade_count":len(trades),"buy_volume_btc":round(buy,4),"sell_volume_btc":round(sell,4),"taker_delta_btc":round(delta,4),"taker_delta_pct":round(delta/total*100 if total else 0,3),"cvd_btc":round(delta,4),"orderbook_bid_btc":round(bid_depth,4),"orderbook_ask_btc":round(ask_depth,4),"orderbook_imbalance":round((bid_depth-ask_depth)/depth if depth else 0,4),"oi_current_btc":round(oi_now,4) if oi_now is not None else None,"oi_5m_ago_btc":None,"oi_change_pct":None}}

async def fetch_okx_last_price():
    async with httpx.AsyncClient(base_url=settings.okx_base_url,timeout=8.0) as c:
        d=await _get(c,"/api/v5/market/ticker",{"instId":settings.okx_instrument})
    return float(d[0]["last"])

async def get_okx_kline_history(interval="15",limit=300,end_ms=None):
    bars={"5":"5m","15":"15m","60":"1H","240":"4H","D":"1D"}; params={"instId":settings.okx_instrument,"bar":bars.get(str(interval),"15m"),"limit":min(max(int(limit),1),300)}
    if end_ms is not None: params["after"]=str(int(end_ms))
    async with httpx.AsyncClient(base_url=settings.okx_base_url,timeout=12.0) as c:
        d=await _get(c,"/api/v5/market/history-candles",params)
    return _candles(d)
