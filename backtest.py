from dataclasses import dataclass
import math
import pandas as pd

from app.config import settings
from app.services.indicators import klines_to_df, ema, rsi, atr, vwap

@dataclass
class Trade:
    direction: str
    entry_time: str
    exit_time: str
    entry: float
    exit: float
    stop: float
    target: float
    gross_r: float
    net_r: float
    outcome: str

def _prepare(rows):
    df = klines_to_df(rows)
    df["ema20"] = ema(df["close"], 20)
    df["ema50"] = ema(df["close"], 50)
    df["rsi14"] = rsi(df["close"], 14)
    df["atr14"] = atr(df, 14)
    df["vwap"] = vwap(df)
    df["vol_avg20"] = df["volume"].rolling(20).mean()
    return df.dropna().reset_index(drop=True)

def _setup_direction(row):
    bull = (
        row["close"] > row["vwap"]
        and row["ema20"] > row["ema50"]
        and 52 <= row["rsi14"] <= 70
        and row["volume"] >= row["vol_avg20"] * 1.05
    )
    bear = (
        row["close"] < row["vwap"]
        and row["ema20"] < row["ema50"]
        and 30 <= row["rsi14"] <= 48
        and row["volume"] >= row["vol_avg20"] * 1.05
    )
    if bull:
        return "LONG"
    if bear:
        return "SHORT"
    return None

def run_backtest(rows, max_hold_bars=4):
    df = _prepare(rows)
    trades = []
    equity_r = 0.0
    peak_r = 0.0
    max_dd_r = 0.0

    fee_slip_pct = (
        settings.backtest_fee_bps_round_trip
        + settings.backtest_slippage_bps_round_trip
    ) / 10000.0

    i = 60
    while i < len(df) - max_hold_bars - 1:
        row = df.iloc[i]
        direction = _setup_direction(row)
        if not direction:
            i += 1
            continue

        entry = float(row["close"])
        risk = max(float(row["atr14"]) * 1.15, entry * 0.001)
        if direction == "LONG":
            stop = entry - risk
            target = entry + risk * 1.5
        else:
            stop = entry + risk
            target = entry - risk * 1.5

        outcome = "EXPIRED"
        exit_price = float(df.iloc[i + max_hold_bars]["close"])
        exit_time = str(df.iloc[i + max_hold_bars]["timestamp"])

        for j in range(i + 1, min(i + max_hold_bars + 1, len(df))):
            bar = df.iloc[j]
            hi, lo = float(bar["high"]), float(bar["low"])

            # Conservative ambiguity rule: if both stop and target occur in same candle, count stop first.
            if direction == "LONG":
                if lo <= stop:
                    exit_price, exit_time, outcome = stop, str(bar["timestamp"]), "STOPPED"
                    break
                if hi >= target:
                    exit_price, exit_time, outcome = target, str(bar["timestamp"]), "TP1"
                    break
            else:
                if hi >= stop:
                    exit_price, exit_time, outcome = stop, str(bar["timestamp"]), "STOPPED"
                    break
                if lo <= target:
                    exit_price, exit_time, outcome = target, str(bar["timestamp"]), "TP1"
                    break

        gross_pnl = (exit_price - entry) if direction == "LONG" else (entry - exit_price)
        gross_r = gross_pnl / risk if risk else 0.0
        cost_abs = entry * fee_slip_pct
        net_r = (gross_pnl - cost_abs) / risk if risk else 0.0

        equity_r += net_r
        peak_r = max(peak_r, equity_r)
        max_dd_r = max(max_dd_r, peak_r - equity_r)

        trades.append(Trade(
            direction=direction,
            entry_time=str(row["timestamp"]),
            exit_time=exit_time,
            entry=round(entry, 2),
            exit=round(exit_price, 2),
            stop=round(stop, 2),
            target=round(target, 2),
            gross_r=round(gross_r, 4),
            net_r=round(net_r, 4),
            outcome=outcome,
        ))
        i += max_hold_bars
    return trades, round(max_dd_r, 4)

def summarize(trades, max_dd_r):
    if not trades:
        return {
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "expired": 0,
            "win_rate_pct": None,
            "profit_factor": None,
            "expectancy_r": None,
            "net_r_total": 0.0,
            "max_drawdown_r": 0.0,
            "by_direction": {},
        }

    wins = [t for t in trades if t.net_r > 0]
    losses = [t for t in trades if t.net_r < 0]
    gross_profit = sum(t.net_r for t in wins)
    gross_loss = abs(sum(t.net_r for t in losses))
    pf = gross_profit / gross_loss if gross_loss > 0 else None
    expectancy = sum(t.net_r for t in trades) / len(trades)

    by_direction = {}
    for d in ("LONG", "SHORT"):
        subset = [t for t in trades if t.direction == d]
        if subset:
            by_direction[d] = {
                "trades": len(subset),
                "win_rate_pct": round(sum(1 for t in subset if t.net_r > 0) / len(subset) * 100, 2),
                "expectancy_r": round(sum(t.net_r for t in subset) / len(subset), 4),
            }

    return {
        "trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "expired": sum(1 for t in trades if t.outcome == "EXPIRED"),
        "win_rate_pct": round(len(wins) / len(trades) * 100, 2),
        "profit_factor": round(pf, 4) if pf is not None else None,
        "expectancy_r": round(expectancy, 4),
        "net_r_total": round(sum(t.net_r for t in trades), 4),
        "max_drawdown_r": max_dd_r,
        "by_direction": by_direction,
    }
