import json
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from app.config import settings

RESOLVED = {"TP1", "TP2", "STOPPED", "EXPIRED"}


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
    if outcome == "STOPPED":
        return -1.0
    if outcome in ("TP1", "TP2"):
        return rr
    if outcome == "EXPIRED":
        return 0.0
    return None


def _stats(rows):
    resolved = [r for r in rows if str(r.get("outcome") or "").upper() in RESOLVED]
    values = [_r(r) for r in resolved]
    values = [x for x in values if x is not None]
    wins = [x for x in values if x > 0]
    losses = [x for x in values if x < 0]
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    return {
        "resolved": len(resolved),
        "win_rate_pct": round(len(wins) / len(resolved) * 100, 2) if resolved else None,
        "profit_factor": round(gross_win / gross_loss, 3) if gross_loss else (999.0 if gross_win else None),
        "expectancy_r": round(sum(values) / len(values), 4) if values else None,
    }


def _adjustment(stats):
    n = int(stats.get("resolved") or 0)
    if n < settings.regime_prior_min_resolved:
        return 0
    exp = float(stats.get("expectancy_r") or 0)
    pf = float(stats.get("profit_factor") or 0)
    wr = float(stats.get("win_rate_pct") or 0)
    points = 0
    if exp >= 0.65 and pf >= 2.5 and wr >= 60:
        points = 8
    elif exp >= 0.40 and pf >= 1.8 and wr >= 55:
        points = 5
    elif exp >= 0.20 and pf >= 1.3 and wr >= 50:
        points = 3
    elif exp <= -0.20 or (pf and pf < 0.8):
        points = -5
    elif exp < 0 or (pf and pf < 1.0):
        points = -3
    cap = int(settings.regime_prior_max_adjustment)
    return max(-cap, min(cap, points))


def init_regime_prior():
    with _connect() as db:
        db.execute("CREATE TABLE IF NOT EXISTS regime_prior_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
        db.execute("""
        CREATE TABLE IF NOT EXISTS regime_prior_stats(
          direction TEXT NOT NULL,
          market_regime TEXT NOT NULL,
          volatility TEXT NOT NULL,
          cross_market TEXT NOT NULL,
          resolved INTEGER NOT NULL,
          win_rate_pct REAL,
          profit_factor REAL,
          expectancy_r REAL,
          adjustment INTEGER NOT NULL,
          PRIMARY KEY(direction,market_regime,volatility,cross_market)
        )
        """)
        frozen = db.execute("SELECT value FROM regime_prior_meta WHERE key='frozen_at'").fetchone()
        if frozen:
            return frozen["value"]

        frozen_at = datetime.now(timezone.utc).isoformat()
        rows = [dict(r) for r in db.execute(
            "SELECT direction,outcome,close_r,rr1,features_json FROM validation_setups WHERE created_at < ?",
            (frozen_at,),
        ).fetchall()]
        groups = defaultdict(list)
        for row in rows:
            try:
                features = json.loads(row.get("features_json") or "{}")
            except Exception:
                features = {}
            key = (
                row.get("direction") or "UNKNOWN",
                features.get("market_regime") or "LEGACY",
                features.get("volatility_bucket") or "LEGACY",
                features.get("cross_market_consensus") or "LEGACY",
            )
            groups[key].append(row)

        for key, group in groups.items():
            stats = _stats(group)
            db.execute(
                "INSERT OR REPLACE INTO regime_prior_stats VALUES(?,?,?,?,?,?,?,?,?)",
                (*key, stats["resolved"], stats["win_rate_pct"], stats["profit_factor"], stats["expectancy_r"], _adjustment(stats)),
            )
        db.execute("INSERT INTO regime_prior_meta(key,value) VALUES('frozen_at',?)", (frozen_at,))
        db.commit()
        return frozen_at


def get_regime_prior(direction, market_regime, volatility, cross_market):
    if not settings.regime_prior_enabled:
        return {"adjustment": 0, "reason": "DISABLED", "resolved": 0}
    try:
        with _connect() as db:
            row = db.execute(
                "SELECT * FROM regime_prior_stats WHERE direction=? AND market_regime=? AND volatility=? AND cross_market=?",
                (direction, market_regime, volatility, cross_market),
            ).fetchone()
            frozen = db.execute("SELECT value FROM regime_prior_meta WHERE key='frozen_at'").fetchone()
    except sqlite3.Error:
        return {"adjustment": 0, "reason": "UNAVAILABLE", "resolved": 0}
    if not row:
        return {"adjustment": 0, "reason": "NO_FROZEN_MATCH", "resolved": 0, "frozen_at": frozen["value"] if frozen else None}
    data = dict(row)
    data["reason"] = "FROZEN_HISTORICAL_PRIOR"
    data["frozen_at"] = frozen["value"] if frozen else None
    return data


def regime_prior_summary():
    try:
        with _connect() as db:
            frozen = db.execute("SELECT value FROM regime_prior_meta WHERE key='frozen_at'").fetchone()
            rows = [dict(r) for r in db.execute(
                "SELECT * FROM regime_prior_stats WHERE adjustment != 0 ORDER BY resolved DESC, adjustment DESC LIMIT 12"
            ).fetchall()]
    except sqlite3.Error:
        return {"frozen_at": None, "active_priors": []}
    return {"frozen_at": frozen["value"] if frozen else None, "active_priors": rows}
