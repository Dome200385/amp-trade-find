import json
import sqlite3
from collections import defaultdict
from app.config import settings

RESOLVED = {"TP1","TP2","STOPPED","EXPIRED"}

def _connect():
    db=sqlite3.connect(settings.database_path)
    db.row_factory=sqlite3.Row
    return db

def _r(row):
    if row.get("close_r") is not None:
        try: return float(row["close_r"])
        except: pass
    outcome=(row.get("outcome") or "").upper()
    rr=float(row.get("rr1") or 1.5)
    if outcome=="STOPPED": return -1.0
    if outcome in ("TP1","TP2"): return rr
    if outcome=="EXPIRED": return 0.0
    return None

def _stats(rows):
    resolved=[r for r in rows if (r.get("outcome") or "").upper() in RESOLVED]
    rv=[_r(r) for r in resolved]
    rv=[x for x in rv if x is not None]
    wins=[x for x in rv if x>0]
    losses=[x for x in rv if x<0]
    gw=sum(wins); gl=abs(sum(losses))
    return {
        "captured":len(rows),
        "resolved":len(resolved),
        "win_rate_pct":round(len(wins)/len(resolved)*100,2) if resolved else None,
        "profit_factor":round(gw/gl,3) if gl else (999.0 if gw else None),
        "expectancy_r":round(sum(rv)/len(rv),4) if rv else None,
    }

def build_regime_analytics():
    with _connect() as db:
        cols={r["name"] for r in db.execute("PRAGMA table_info(validation_setups)").fetchall()}
        if "features_json" not in cols:
            return {"overall":_stats([]),"dimensions":{},"leaderboard":[]}
        rows=[dict(r) for r in db.execute("""
          SELECT direction,outcome,close_r,rr1,features_json
          FROM validation_setups
          ORDER BY created_at DESC
        """).fetchall()]

    enriched=[]
    for r in rows:
        try: f=json.loads(r.get("features_json") or "{}")
        except: f={}
        r["features"]=f
        enriched.append(r)

    dims={
        "market_regime":defaultdict(list),
        "volatility":defaultdict(list),
        "trend_1h":defaultdict(list),
        "trend_15m":defaultdict(list),
        "cross_market":defaultdict(list),
        "weekday_utc":defaultdict(list),
        "hour_utc":defaultdict(list),
    }

    for r in enriched:
        f=r["features"]
        dims["market_regime"][f.get("market_regime") or "LEGACY"].append(r)
        dims["volatility"][f.get("volatility_bucket") or "LEGACY"].append(r)
        dims["trend_1h"][f.get("trend_1h") or "LEGACY"].append(r)
        dims["trend_15m"][f.get("trend_15m") or "LEGACY"].append(r)
        dims["cross_market"][f.get("cross_market_consensus") or "LEGACY"].append(r)
        dims["weekday_utc"][str(f.get("captured_weekday_utc","LEGACY"))].append(r)
        dims["hour_utc"][str(f.get("captured_hour_utc","LEGACY"))].append(r)

    out={"overall":_stats(enriched),"dimensions":{},"leaderboard":[]}
    for name,groups in dims.items():
        out["dimensions"][name]={k:_stats(v) for k,v in sorted(groups.items())}

    combos=defaultdict(list)
    for r in enriched:
        f=r["features"]
        key=(
            r.get("direction") or "UNKNOWN",
            f.get("market_regime") or "LEGACY",
            f.get("volatility_bucket") or "LEGACY",
            f.get("cross_market_consensus") or "LEGACY",
        )
        combos[key].append(r)

    board=[]
    for (direction,regime,vol,cross),group in combos.items():
        st=_stats(group)
        if not st["resolved"]:
            continue
        exp=st["expectancy_r"] or 0
        pf=min(st["profit_factor"] or 0,3)
        sample_weight=min(st["resolved"]/20,1)
        rank=round((exp*50 + pf*12 + (st["win_rate_pct"] or 0)*0.2)*sample_weight,3)
        board.append({
            "direction":direction,"market_regime":regime,"volatility":vol,
            "cross_market":cross,**st,"rank_score":rank
        })
    board.sort(key=lambda x:(x["rank_score"],x["resolved"]),reverse=True)
    out["leaderboard"]=board[:12]
    return out
