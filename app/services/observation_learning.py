import json, sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from app.config import settings
from app.services.setup_features import extract_setup_features
from app.services.validation_evaluator import evaluate_row

RESOLVED=("TP1","TP2","STOPPED","EXPIRED")

def _connect():
    db=sqlite3.connect(settings.database_path); db.row_factory=sqlite3.Row; return db

def init_observation_db():
    with _connect() as db:
        db.execute('''CREATE TABLE IF NOT EXISTS observation_setups(
          observation_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
          strategy_version TEXT NOT NULL, symbol TEXT, direction TEXT NOT NULL, state_at_capture TEXT,
          score INTEGER NOT NULL, quality_grade TEXT, setup_grade TEXT, confidence_pct REAL,
          entry_low REAL, entry_high REAL, entry_center REAL, stop REAL, target1 REAL, target2 REAL,
          rr1 REAL, rr2 REAL, entry_reached INTEGER NOT NULL DEFAULT 0, entry_reached_at TEXT,
          entry_fill_price REAL, outcome TEXT NOT NULL DEFAULT 'WAITING_ENTRY', outcome_at TEXT,
          mfe_price REAL, mae_price REAL, mfe_r REAL, mae_r REAL, close_price REAL, close_r REAL,
          observation_reason TEXT, features_json TEXT, signal_json TEXT)''')
        db.execute("CREATE INDEX IF NOT EXISTS idx_obs_status ON observation_setups(outcome,created_at)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_obs_bucket ON observation_setups(direction,score,created_at)")
        db.commit()

def observation_policy(signal:dict):
    if not settings.observation_learning_enabled: return False,"OBSERVATION_DISABLED"
    direction=signal.get("directional_bias")
    if direction not in ("LONG","SHORT"): return False,"OBSERVATION_NO_DIRECTION"
    score=int(signal.get("long_score",0) if direction=="LONG" else signal.get("short_score",0))
    if score < settings.observation_min_score: return False,"OBSERVATION_SCORE_TOO_LOW"
    if not signal.get("entry_decision"): return False,"OBSERVATION_NO_ENTRY_PLAN"
    return True,"OBSERVATION_POLICY_OK"

def capture_observation(snapshot:dict, signal:dict, reason:str):
    ok,why=observation_policy(signal)
    if not ok: return False,why
    e=signal["entry_decision"]; direction=signal["directional_bias"]
    score=int(signal.get("long_score",0) if direction=="LONG" else signal.get("short_score",0))
    now=datetime.now(timezone.utc); oid="OBS-"+str(signal.get("signal_id") or now.timestamp())
    q=signal.get("signal_quality") or {}; a=signal.get("adaptive_assessment") or {}
    features=extract_setup_features(snapshot,signal)
    with _connect() as db:
        active=db.execute("SELECT COUNT(*) FROM observation_setups WHERE outcome IN ('WAITING_ENTRY','ACTIVE')").fetchone()[0]
        if active >= settings.observation_max_active: return False,"OBSERVATION_MAX_ACTIVE"
        old=db.execute('''SELECT entry_center FROM observation_setups WHERE direction=? AND outcome IN ('WAITING_ENTRY','ACTIVE')
          AND created_at >= datetime('now', ?) ORDER BY created_at DESC LIMIT 1''',
          (direction,f"-{settings.observation_dedupe_minutes} minutes")).fetchone()
        if old:
            op=float(old[0] or 0); np=float(e.get("entry_center") or 0)
            if op and abs(np-op)/op*100 < settings.observation_dedupe_price_pct:
                return False,"OBSERVATION_DUPLICATE"
        db.execute('''INSERT OR IGNORE INTO observation_setups(
          observation_id,created_at,updated_at,strategy_version,symbol,direction,state_at_capture,score,
          quality_grade,setup_grade,confidence_pct,entry_low,entry_high,entry_center,stop,target1,target2,rr1,rr2,
          mfe_price,mae_price,observation_reason,features_json,signal_json)
          VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(
          oid,now.isoformat(),now.isoformat(),settings.strategy_version,signal.get("symbol"),direction,signal.get("state"),score,
          q.get("grade"),a.get("setup_grade"),signal.get("confidence_pct") or a.get("confidence_pct"),
          e.get("entry_low"),e.get("entry_high"),e.get("entry_center"),e.get("stop"),e.get("target1"),e.get("target2"),
          e.get("rr_target1"),e.get("rr_target2"),signal.get("price"),signal.get("price"),reason,
          json.dumps(features,separators=(",",":")),json.dumps(signal,separators=(",",":"))))
        db.commit()
    return True,oid

def _active():
    with _connect() as db:
        return [dict(r) for r in db.execute("SELECT * FROM observation_setups WHERE outcome IN ('WAITING_ENTRY','ACTIVE') ORDER BY created_at").fetchall()]

def evaluate_observations(price:float):
    rows=_active(); updates=[]; now=datetime.now(timezone.utc)
    with _connect() as db:
        for row in rows:
            r=evaluate_row(row,float(price),now)
            if r["outcome"]=="WAITING_ENTRY": continue
            fields=["outcome=?","updated_at=?"]; vals=[r["outcome"],now.isoformat()]
            if r.get("entry_reached") is not None:
                fields.append("entry_reached=?"); vals.append(1 if r["entry_reached"] else 0)
                if r["entry_reached"] and not row.get("entry_reached_at"):
                    fields.append("entry_reached_at=?"); vals.append(now.isoformat())
            for k in ("entry_fill_price","mfe_price","mae_price","mfe_r","mae_r"):
                if r.get(k) is not None: fields.append(f"{k}=?"); vals.append(r[k])
            if r["outcome"] not in ("WAITING_ENTRY","ACTIVE"):
                fields += ["outcome_at=?","close_price=?","close_r=?"]
                vals += [now.isoformat(),float(price),r.get("close_r")]
            vals.append(row["observation_id"])
            db.execute(f"UPDATE observation_setups SET {','.join(fields)} WHERE observation_id=?",vals)
            updates.append({"observation_id":row["observation_id"],"outcome":r["outcome"]})
        db.commit()
    return {"checked":len(rows),"updates":updates}

def _bucket(rows,keyfn):
    groups=defaultdict(list)
    for r in rows: groups[keyfn(r)].append(r)
    out=[]
    for key,rs in groups.items():
        resolved=[x for x in rs if x.get("outcome") in RESOLVED]
        if not resolved: continue
        wins=sum(x.get("outcome") in ("TP1","TP2") for x in resolved)
        pos=sum(max(float(x.get("close_r") or 0),0) for x in resolved); neg=sum(abs(min(float(x.get("close_r") or 0),0)) for x in resolved)
        exp=sum(float(x.get("close_r") or 0) for x in resolved)/len(resolved)
        out.append({"bucket":key,"n":len(resolved),"win_pct":round(wins/len(resolved)*100,1),"pf":round(pos/neg,2) if neg else None,"exp_r":round(exp,2)})
    return sorted(out,key=lambda x:(x["n"],x["exp_r"]),reverse=True)[:8]

def observation_stats(hours=168):
    try:
        with _connect() as db:
            rows=[dict(r) for r in db.execute("SELECT * FROM observation_setups WHERE created_at >= datetime('now', ?) ORDER BY created_at DESC",(f"-{int(hours)} hours",)).fetchall()]
    except sqlite3.Error: rows=[]
    for r in rows:
        try: r["features"]=json.loads(r.get("features_json") or "{}")
        except Exception: r["features"]={}
    resolved=[r for r in rows if r.get("outcome") in RESOLVED]
    return {"window_hours":hours,"captured":len(rows),"waiting":sum(r.get("outcome")=="WAITING_ENTRY" for r in rows),
      "active":sum(r.get("outcome")=="ACTIVE" for r in rows),"resolved":len(resolved),
      "missed_entry":sum(r.get("outcome")=="MISSED_ENTRY" for r in rows),
      "by_direction":_bucket(rows,lambda r:r.get("direction") or "UNKNOWN"),
      "by_regime":_bucket(rows,lambda r:(r.get("features") or {}).get("market_regime") or "UNKNOWN"),
      "by_condition":_bucket(rows,lambda r:" / ".join(str(x or "UNKNOWN") for x in (r.get("direction"),(r.get("features") or {}).get("market_regime"),(r.get("features") or {}).get("volatility_bucket"),(r.get("features") or {}).get("cross_market_consensus")))),
      "last":rows[0] if rows else None}
