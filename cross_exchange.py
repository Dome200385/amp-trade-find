import asyncio
from app.services.binance_market import fetch_binance_bundle
from app.services.okx_market import fetch_okx_bundle
from app.services.kraken_market import fetch_kraken_bundle
from app.services.coinbase_market import fetch_coinbase_bundle

def err(name,typ,e): return {"venue":name,"market_type":typ,"trade_count":0,"buy_volume_btc":0.0,"sell_volume_btc":0.0,"taker_delta_btc":0.0,"taker_delta_pct":0.0,"orderbook_imbalance":None,"available":False,"error":str(e)[:240]}
def venue(name,typ,of): return {"venue":name,"market_type":typ,"trade_count":of["trade_count"],"buy_volume_btc":of["buy_volume_btc"],"sell_volume_btc":of["sell_volume_btc"],"taker_delta_btc":of["taker_delta_btc"],"taker_delta_pct":of["taker_delta_pct"],"orderbook_imbalance":of["orderbook_imbalance"],"available":True,"error":None}
async def fv(name,typ,fn):
    try: return venue(name,typ,(await fn())["orderflow"])
    except Exception as e: return err(name,typ,e)
async def build_cross_exchange(orderflow,primary_source="BYBIT",source_errors=None):
    source_errors=source_errors or {}; defs={"BYBIT":("FUTURES",None),"BINANCE":("FUTURES",fetch_binance_bundle),"OKX":("SWAP",fetch_okx_bundle),"KRAKEN":("SPOT",fetch_kraken_bundle),"COINBASE":("SPOT",fetch_coinbase_bundle)}; venues={}; tasks=[]; names=[]
    for name,(typ,fn) in defs.items():
        if name==primary_source: venues[name]=venue(name,typ,orderflow)
        elif name in source_errors or fn is None: venues[name]=err(name,typ,source_errors.get(name,"Unavailable"))
        else: names.append(name); tasks.append(fv(name,typ,fn))
    if tasks:
        for name,res in zip(names,await asyncio.gather(*tasks)): venues[name]=res
    ordered=[venues[n] for n in ("BYBIT","BINANCE","OKX","KRAKEN","COINBASE")]; av=[v for v in ordered if v["available"]]
    lc=sum(1 for v in av if v["taker_delta_pct"]>=5 and (v["orderbook_imbalance"] is None or v["orderbook_imbalance"]>=0.03)); sc=sum(1 for v in av if v["taker_delta_pct"]<=-5 and (v["orderbook_imbalance"] is None or v["orderbook_imbalance"]<=-0.03)); n=len(av)
    if lc>=2 and lc>sc: cons,strength="LONG",lc/n
    elif sc>=2 and sc>lc: cons,strength="SHORT",sc/n
    elif lc and sc: cons,strength="MIXED",max(lc,sc)/n
    else: cons,strength="NEUTRAL",0.0
    return {"bybit":venues["BYBIT"],"binance":venues["BINANCE"],"okx":venues["OKX"],"kraken":venues["KRAKEN"],"coinbase":venues["COINBASE"],"long_confirmations":lc,"short_confirmations":sc,"available_venues":n,"consensus":cons,"consensus_strength":round(strength,3),"available_names":[v["venue"] for v in av]}
