from typing import Literal, Any
from pydantic import BaseModel

class TimeframeIndicators(BaseModel):
    timeframe: str
    close: float
    ema20: float
    ema50: float
    vwap: float
    rsi14: float
    atr14: float
    volume: float
    volume_ratio: float

class VenueFlow(BaseModel):
    venue: str
    market_type: str
    trade_count: int
    buy_volume_btc: float
    sell_volume_btc: float
    taker_delta_btc: float
    taker_delta_pct: float
    orderbook_imbalance: float | None = None
    available: bool = True
    error: str | None = None

class CrossExchangeFlow(BaseModel):
    bybit: VenueFlow
    binance: VenueFlow
    okx: VenueFlow
    kraken: VenueFlow
    coinbase: VenueFlow
    long_confirmations: int
    short_confirmations: int
    available_venues: int
    consensus: Literal["LONG", "SHORT", "MIXED", "NEUTRAL"]
    consensus_strength: float
    available_names: list[str]

class OrderFlowSnapshot(BaseModel):
    trade_count: int
    buy_volume_btc: float
    sell_volume_btc: float
    taker_delta_btc: float
    taker_delta_pct: float
    cvd_btc: float
    orderbook_bid_btc: float
    orderbook_ask_btc: float
    orderbook_imbalance: float
    oi_current_btc: float | None = None
    oi_5m_ago_btc: float | None = None
    oi_change_pct: float | None = None

class MarketSnapshot(BaseModel):
    symbol: str
    primary_source: str
    source_degraded: bool
    source_errors: dict[str, str]
    price: float
    bid: float
    ask: float
    spread_bps: float
    funding_rate: float | None = None
    open_interest: float | None = None
    change_24h_pct: float | None = None
    tf_5m: TimeframeIndicators
    tf_15m: TimeframeIndicators
    tf_1h: TimeframeIndicators
    orderflow: OrderFlowSnapshot
    cross_exchange: CrossExchangeFlow
    live_cvd: dict[str, Any]
    event_risk: dict[str, Any]

class ScoreComponent(BaseModel):
    name: str
    long_points: int
    short_points: int
    max_points: int
    detail: str

class TradePlan(BaseModel):
    direction: Literal["LONG", "SHORT"]
    entry: float
    stop: float
    target1: float
    target2: float
    rr_target1: float
    rr_target2: float
    validity_minutes: int

class SignalResponse(BaseModel):
    signal_id: str
    symbol: str
    price: float
    state: Literal["NO_TRADE", "MARKET_WATCH", "SETUP_FORMING"]
    candidate_opportunity: Literal["NONE", "LONG", "SHORT"]
    long_score: int
    short_score: int
    market_bias: Literal["BULLISH", "NEUTRAL", "BEARISH"]
    setup: str
    components: list[ScoreComponent]
    blockers: list[str]
    trade_plan: TradePlan | None = None
    paper_mode: bool
    note: str
