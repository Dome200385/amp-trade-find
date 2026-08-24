import json
import sqlite3
from collections import defaultdict
from app.config import settings
from app.services.setup_features import extract_setup_features

SOURCE_STRATEGY = "FIND-V9.9-1"
FEATURES = ("direction", "market_regime", "volatility_bucket", "cross_market_consensus")


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
    vals = [v for v in (_r(r) for r in rows) if v is not None]
    wins = [v for v in vals if v > 0]
    losses = [v for v in vals if v < 0]
    pos, neg = sum(wins), abs(sum(losses))
    n = len(vals)
    return {
        "n": n,
        "win_rate_pct": round(100 * len(wins) / n, 2) if n else None,
        "profit_factor": round(pos / neg, 3) if neg else (999.0 if pos else None),
        "expectancy_r": round(sum(vals) / n, 4) if n else None,
    }


def _load_source_rows():
    try:
        with _connect() as db:
            raw = [dict(r) for r in db.execute(
                """SELECT direction,outcome,close_r,rr1,features_json
                   FROM validation_setups
                   WHERE strategy_version=?
                     AND outcome IN ('TP1','TP2','STOPPED','EXPIRED')""",
                (SOURCE_STRATEGY,),
            ).fetchall()]
    except sqlite3.Error:
        return []
    rows = []
    for r in raw:
        try:
            f = json.loads(r.get("features_json") or "{}")
        except Exception:
            f = {}
        r.update({
            "direction": r.get("direction") or "UNKNOWN",
            "market_regime": f.get("market_regime") or "LEGACY",
            "volatility_bucket": f.get("volatility_bucket") or "LEGACY",
            "cross_market_consensus": f.get("cross_market_consensus") or "LEGACY",
        })
        rows.append(r)
    return rows


def build_v910_selection_model():
    rows = _load_source_rows()
    evidence = []
    for feature in FEATURES:
        groups = defaultdict(list)
        for r in rows:
            groups[str(r.get(feature) or "UNKNOWN")].append(r)
        for value, group in groups.items():
            s = _stats(group)
            if s["n"] < settings.v910_min_feature_samples:
                label = "INSUFFICIENT"
            elif (s["expectancy_r"] or 0) >= settings.v910_support_expectancy_r and \
                 (s["profit_factor"] or 0) >= settings.v910_support_profit_factor and \
                 (s["win_rate_pct"] or 0) >= settings.v910_support_win_rate_pct:
                label = "SUPPORTED"
            elif (s["expectancy_r"] or 0) <= settings.v910_reject_expectancy_r and \
                 ((s["profit_factor"] is not None and s["profit_factor"] < settings.v910_reject_profit_factor) or
                  (s["win_rate_pct"] is not None and s["win_rate_pct"] < settings.v910_reject_win_rate_pct)):
                label = "WEAK"
            else:
                label = "NEUTRAL"
            evidence.append({"feature": feature, "value": value, "label": label, **s})
    return {
        "source_strategy": SOURCE_STRATEGY,
        "source": _stats(rows),
        "source_frozen": len(rows) >= settings.v99_forward_target_resolved,
        "evidence": evidence,
        "rules": {
            "min_feature_samples": settings.v910_min_feature_samples,
            "required_support_votes": settings.v910_required_support_votes,
            "support_expectancy_r": settings.v910_support_expectancy_r,
            "support_profit_factor": settings.v910_support_profit_factor,
            "support_win_rate_pct": settings.v910_support_win_rate_pct,
            "reject_expectancy_r": settings.v910_reject_expectancy_r,
        },
    }


def evaluate_v910_selection(snapshot: dict, signal: dict) -> dict:
    if not settings.v910_selection_enabled:
        return {"blocked": False, "reason": "DISABLED"}
    direction = signal.get("directional_bias") or "NONE"
    if direction not in ("LONG", "SHORT"):
        return {"blocked": False, "reason": "NO_DIRECTION"}
    model = build_v910_selection_model()
    if not model.get("source_frozen"):
        # Never learn V9.10 selection from an incomplete V9.9 cohort.
        return {"blocked": True, "reason": "V910_SOURCE_NOT_FROZEN", "model": model}
    f = extract_setup_features(snapshot, signal)
    current = {
        "direction": direction,
        "market_regime": f.get("market_regime") or "LEGACY",
        "volatility_bucket": f.get("volatility_bucket") or "LEGACY",
        "cross_market_consensus": f.get("cross_market_consensus") or "LEGACY",
    }
    matched = [e for e in model["evidence"] if current.get(e["feature"]) == e["value"]]
    weak = [e for e in matched if e["label"] == "WEAK"]
    supported = [e for e in matched if e["label"] == "SUPPORTED"]
    if weak:
        return {"blocked": True, "reason": "V910_WEAK_EVIDENCE", "support_votes": len(supported), "current": current, "matched": matched}
    if len(supported) < settings.v910_required_support_votes:
        return {"blocked": True, "reason": "V910_INSUFFICIENT_SUPPORT", "support_votes": len(supported), "current": current, "matched": matched}
    return {"blocked": False, "reason": "V910_SELECTED", "support_votes": len(supported), "current": current, "matched": matched}
