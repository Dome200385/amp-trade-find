from datetime import datetime, timezone

def build_notification_payload(signal: dict, snapshot: dict) -> dict:
    candidate = signal.get("candidate_opportunity", "NONE")
    plan = signal.get("trade_plan")

    actionable_paper = candidate in ("LONG", "SHORT") and plan is not None

    if candidate == "LONG":
        title = "AMP FIND · LONG SETUP"
    elif candidate == "SHORT":
        title = "AMP FIND · SHORT SETUP"
    elif signal.get("state") == "SETUP_FORMING":
        title = "AMP FIND · SETUP FORMING"
    else:
        title = "AMP FIND · MARKET UPDATE"

    body = (
        f'BTC {snapshot["price"]:.2f} · '
        f'L {signal["long_score"]} / S {signal["short_score"]}'
    )

    if actionable_paper:
        body += (
            f' · Entry {plan["entry"]:.2f}'
            f' · SL {plan["stop"]:.2f}'
            f' · TP1 {plan["target1"]:.2f}'
        )

    return {
        "notification_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "paper_mode": bool(signal.get("paper_mode", True)),
        "should_notify_foreground": actionable_paper,
        "should_notify_push": False,
        "push_block_reason": "PAPER_MODE_VALIDATION_REQUIRED",
        "dedupe_key": f'{candidate}:{signal.get("setup","NONE")}:{round(snapshot["price"], -1)}',
        "title": title,
        "body": body,
        "direction": candidate,
        "signal_id": signal.get("signal_id"),
        "state": signal.get("state"),
        "long_score": signal.get("long_score"),
        "short_score": signal.get("short_score"),
        "trade_plan": plan,
        "blockers": signal.get("blockers", []),
        "warnings": signal.get("warnings", []),
        "signal_quality": signal.get("signal_quality", {}),
        "deep_link": f'amptradefind://signal/{signal.get("signal_id","")}',
    }
