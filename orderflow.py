from typing import Any

def _f(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

def build_orderflow(trades: list[dict], orderbook: dict, oi_rows: list[dict]) -> dict:
    buy_volume = 0.0
    sell_volume = 0.0

    # Bybit public trade side is the taker side.
    for trade in trades:
        size = _f(trade.get("size"))
        side = str(trade.get("side", "")).lower()
        if side == "buy":
            buy_volume += size
        elif side == "sell":
            sell_volume += size

    total = buy_volume + sell_volume
    delta = buy_volume - sell_volume
    delta_pct = (delta / total * 100.0) if total else 0.0

    bids = orderbook.get("b", []) or []
    asks = orderbook.get("a", []) or []
    bid_depth = sum(_f(level[1]) for level in bids if len(level) >= 2)
    ask_depth = sum(_f(level[1]) for level in asks if len(level) >= 2)
    depth_total = bid_depth + ask_depth
    imbalance = ((bid_depth - ask_depth) / depth_total) if depth_total else 0.0

    # REST recent-trade CVD is a snapshot CVD over the returned trade window.
    # Persistent CVD will replace this in the WebSocket collector milestone.
    cvd = delta

    oi_sorted = sorted(
        oi_rows,
        key=lambda x: int(x.get("timestamp", 0) or 0),
        reverse=True,
    )
    oi_current = _f(oi_sorted[0].get("openInterest")) if oi_sorted else None
    oi_previous = _f(oi_sorted[1].get("openInterest")) if len(oi_sorted) > 1 else None

    if oi_current is not None and oi_previous not in (None, 0):
        oi_change_pct = ((oi_current - oi_previous) / oi_previous) * 100.0
    else:
        oi_change_pct = None

    return {
        "trade_count": len(trades),
        "buy_volume_btc": round(buy_volume, 4),
        "sell_volume_btc": round(sell_volume, 4),
        "taker_delta_btc": round(delta, 4),
        "taker_delta_pct": round(delta_pct, 3),
        "cvd_btc": round(cvd, 4),
        "orderbook_bid_btc": round(bid_depth, 4),
        "orderbook_ask_btc": round(ask_depth, 4),
        "orderbook_imbalance": round(imbalance, 4),
        "oi_current_btc": round(oi_current, 4) if oi_current is not None else None,
        "oi_5m_ago_btc": round(oi_previous, 4) if oi_previous is not None else None,
        "oi_change_pct": round(oi_change_pct, 4) if oi_change_pct is not None else None,
    }
