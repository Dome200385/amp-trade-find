import math
import pandas as pd

def klines_to_df(rows: list[list[str]]) -> pd.DataFrame:
    # Bybit kline layout:
    # startTime, openPrice, highPrice, lowPrice, closePrice, volume, turnover
    df = pd.DataFrame(
        rows,
        columns=["timestamp", "open", "high", "low", "close", "volume", "turnover"],
    )
    for c in ["open", "high", "low", "close", "volume", "turnover"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["timestamp"] = pd.to_datetime(pd.to_numeric(df["timestamp"]), unit="ms", utc=True)
    return df.dropna().reset_index(drop=True)

def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    out = 100 - (100 / (1 + rs))
    return out.fillna(50.0)

def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean().bfill()

def vwap(df: pd.DataFrame) -> pd.Series:
    typical = (df["high"] + df["low"] + df["close"]) / 3.0
    denom = df["volume"].cumsum().replace(0, float("nan"))
    return ((typical * df["volume"]).cumsum() / denom).ffill()

def build_indicators(rows: list[list[str]], timeframe: str) -> dict:
    df = klines_to_df(rows)
    if len(df) < 60:
        raise ValueError(f"Not enough {timeframe} candles: {len(df)}")

    df["ema20"] = ema(df["close"], 20)
    df["ema50"] = ema(df["close"], 50)
    df["rsi14"] = rsi(df["close"], 14)
    df["atr14"] = atr(df, 14)
    df["vwap"] = vwap(df)
    df["vol_sma20"] = df["volume"].rolling(20).mean()

    last = df.iloc[-1]
    vol_avg = float(last["vol_sma20"]) if not math.isnan(float(last["vol_sma20"])) else float(last["volume"])
    volume_ratio = float(last["volume"]) / vol_avg if vol_avg > 0 else 1.0

    return {
        "timeframe": timeframe,
        "close": round(float(last["close"]), 2),
        "ema20": round(float(last["ema20"]), 2),
        "ema50": round(float(last["ema50"]), 2),
        "vwap": round(float(last["vwap"]), 2),
        "rsi14": round(float(last["rsi14"]), 2),
        "atr14": round(float(last["atr14"]), 2),
        "volume": float(last["volume"]),
        "volume_ratio": round(volume_ratio, 3),
    }
