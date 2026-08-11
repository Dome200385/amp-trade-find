import asyncio
import httpx
from app.config import settings

def _f(v,d=0.0):
    try: return float(v)
    except (TypeError,ValueError): return d
async def _get(c,path,params=None):
    r=await c.get(path,params=params or {}); r.raise_for_status(); j=r.json()
    if j.get("error"): raise RuntimeError("Kraken: "+"; ".join(j["error"]))
    return j.get("result",{})
def _key(d):
    for k in d:
        if k!="last": return k
    raise RuntimeError("Kraken market key missing")
def _ohlc(rows):
    return [[str(int(x[0])*1000),str(x[1]),str(x[2]),str(x[3]),str(x[4]),str(x[6]),str(_f(x[5])*_f(x[6]))] for x in rows]
async def fetch_kraken_bundle():
    pair=settings.kraken_pair
    async with httpx.AsyncClient(base_url=settings.kraken_base_url,timeout=12.0,headers={"User-Agent":"AMP-TRADE-FIND/0.8.2"}) as c:
        o5,o15,o60,tick,trades,depth=await asyncio.gather(_get(c,"/0/public/OHLC",{"pair":pair,"interval":5}),_get(c,"/0/public/OHLC",{"pair":pair,"interval":15}),_get(c,"/0/public/OHLC",{"pair":pair,"interval":60}),_get(c,"/0/public/Ticker",{"pair":pair}),_get(c,"/0/public/Trades",{"pair":pair}),_get(c,"/0/public/Depth",{"pair":pair,"count":200}))
    t=tick[_key(tick)]; trs=trades[_key(trades)]; dep=depth[_key(depth)]; buy=sell=0.0
    for tr in trs:
        q=_f(tr[1]); side=str(tr[3]).lower()
        if side=="b": buy+=q
        elif side=="s": sell+=q
    total=buy+sell; delta=buy-sell; bd=sum(_f(x[1]) for x in dep.get("bids",[])); ad=sum(_f(x[1]) for x in dep.get("asks",[])); dt=bd+ad
    last=_f(t.get("c",[0])[0]); op=_f(t.get("o",0)); pct=(last-op)/op if op else None
    return {"source":"KRAKEN","5":_ohlc(o5[_key(o5)]),"15":_ohlc(o15[_key(o15)]),"60":_ohlc(o60[_key(o60)]),
      "ticker":{"lastPrice":str(last),"bid1Price":str(_f(t.get("b",[0])[0])),"ask1Price":str(_f(t.get("a",[0])[0])),"fundingRate":"","openInterest":"","price24hPcnt":str(pct) if pct is not None else ""},
      "orderflow":{"trade_count":len(trs),"buy_volume_btc":round(buy,4),"sell_volume_btc":round(sell,4),"taker_delta_btc":round(delta,4),"taker_delta_pct":round(delta/total*100 if total else 0,3),"cvd_btc":round(delta,4),"orderbook_bid_btc":round(bd,4),"orderbook_ask_btc":round(ad,4),"orderbook_imbalance":round((bd-ad)/dt if dt else 0,4),"oi_current_btc":None,"oi_5m_ago_btc":None,"oi_change_pct":None}}
async def fetch_kraken_last_price():
    async with httpx.AsyncClient(base_url=settings.kraken_base_url,timeout=8.0) as c:
        d=await _get(c,"/0/public/Ticker",{"pair":settings.kraken_pair})
    return float(d[_key(d)]["c"][0])
async def get_kraken_kline_history(interval="15",limit=720,end_ms=None):
    iv={"5":5,"15":15,"60":60,"240":240,"D":1440}.get(str(interval),15); params={"pair":settings.kraken_pair,"interval":iv}
    if end_ms is not None: params["since"]=max(0,int(end_ms//1000)-int(limit)*iv*60)
    async with httpx.AsyncClient(base_url=settings.kraken_base_url,timeout=12.0) as c:
        d=await _get(c,"/0/public/OHLC",params)
    return _ohlc(d[_key(d)])[-min(int(limit),720):]
