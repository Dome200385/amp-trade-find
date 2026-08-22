from app.config import settings
from app.services.forward_diagnostics import build_forward_diagnostics
from app.services.setup_features import extract_setup_features

def evaluate_v99_filter(snapshot: dict, signal: dict) -> dict:
    if not settings.v99_filter_enabled:
        return {"blocked": False, "reason": "DISABLED"}
    direction = signal.get("directional_bias") or "NONE"
    if direction not in ("LONG", "SHORT"):
        return {"blocked": False, "reason": "NO_DIRECTION"}

    features = extract_setup_features(snapshot, signal)
    current = {
        "direction": direction,
        "regime": features.get("market_regime") or "LEGACY",
        "volatility": features.get("volatility_bucket") or "LEGACY",
        "cross_market": features.get("cross_market_consensus") or "LEGACY",
    }
    diagnostics = build_forward_diagnostics()
    for bucket in diagnostics.get("weak_buckets", []) or []:
        if all(bucket.get(k) == current[k] for k in ("direction", "regime", "volatility", "cross_market")):
            return {
                "blocked": True,
                "reason": "V99_FORWARD_WEAK_BUCKET",
                "current": current,
                "matched_bucket": bucket,
            }
    return {"blocked": False, "reason": "NO_WEAK_BUCKET_MATCH", "current": current}
