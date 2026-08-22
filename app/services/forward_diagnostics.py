import json
import sqlite3
from collections import defaultdict
from app.config import settings

SOURCE_STRATEGY = "FIND-V9.8-1"

def _connect():
    db = sqlite3.connect(settings.database_path)
    db.row_factory = sqlite3.Row
    return db

def _r(row):
    if row.get("close_r") is not None:
        try:
            return float(row["close_r"])
        except Exception:
            pass
    outcome = str(row.get("outcome") or "").upper()
    rr = float(row.get("rr1") or 1.5)
    if outcome in ("TP1", "TP2"):
        return rr
    if outcome == "STOPPED":
        return -1.0
    if outcome == "EXPIRED":
        return 0.0
    return None

def _stats(rows):
    vals = [_r(r) for r in rows]
    vals = [x for x in vals if x is not None]
    wins = [x for x in vals if x > 0]
    losses = [x for x in vals if x < 0]
    pos = sum(wins)
    neg = abs(sum(losses))
    n = len(vals)
    return {
        "resolved": n,
        "win_rate_pct": round(len(wins) / n * 100, 2) if n else None,
        "profit_factor": round(pos / neg, 3) if neg else (999.0 if pos else None),
        "expectancy_r": round(sum(vals) / n, 4) if n else None,
    }

def build_forward_diagnostics():
    try:
        with _connect() as db:
            rows = [dict(r) for r in db.execute(
                """
                SELECT direction, setup_grade, confidence_pct, score, outcome, close_r, rr1,
                       quality_grade, features_json
                FROM validation_setups
                WHERE strategy_version=?
                  AND outcome IN ('TP1','TP2','STOPPED','EXPIRED')
                """,
                (SOURCE_STRATEGY,),
            ).fetchall()]
    except sqlite3.Error:
        rows = []

    enriched = []
    for r in rows:
        try:
            features = json.loads(r.get("features_json") or "{}")
        except Exception:
            features = {}
        r["features"] = features
        enriched.append(r)

    combos = defaultdict(list)
    for r in enriched:
        f = r["features"]
        key = (
            r.get("direction") or "UNKNOWN",
            f.get("market_regime") or "LEGACY",
            f.get("volatility_bucket") or "LEGACY",
            f.get("cross_market_consensus") or "LEGACY",
        )
        combos[key].append(r)

    buckets = []
    for key, group in combos.items():
        buckets.append({
            "direction": key[0],
            "regime": key[1],
            "volatility": key[2],
            "cross_market": key[3],
            **_stats(group),
        })
    buckets.sort(key=lambda x: x["resolved"], reverse=True)

    weak = []
    strong = []
    for b in buckets:
        if b["resolved"] < settings.v99_min_bucket_samples:
            continue
        exp = b.get("expectancy_r")
        pf = b.get("profit_factor")
        wr = b.get("win_rate_pct")
        if exp is not None and exp <= settings.v99_block_expectancy_r and (
            (pf is not None and pf < settings.v99_block_profit_factor)
            or (wr is not None and wr < settings.v99_block_win_rate_pct)
        ):
            weak.append(b)
        elif (exp or 0) >= 0.25 and (pf or 0) >= 1.4 and (wr or 0) >= 50:
            strong.append(b)

    weak.sort(key=lambda x: (x.get("expectancy_r", 999), -x["resolved"]))
    strong.sort(key=lambda x: (x.get("expectancy_r", -999), x["resolved"]), reverse=True)
    return {
        "source_strategy": SOURCE_STRATEGY,
        "overall": _stats(enriched),
        "buckets": buckets,
        "weak_buckets": weak[:12],
        "strong_buckets": strong[:12],
        "rules": {
            "min_samples": settings.v99_min_bucket_samples,
            "max_expectancy_r": settings.v99_block_expectancy_r,
            "max_profit_factor": settings.v99_block_profit_factor,
            "max_win_rate_pct": settings.v99_block_win_rate_pct,
        },
    }
