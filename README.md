# AMP TRADE FIND – Backend V6

V5 adds the first **validation and anti-overtrading layer**.

## New in V5

### Historical backtest endpoint
`GET /api/v1/backtest?interval=15&candles=1000`

The backend fetches historical Bybit klines and replays a deliberately simple
technical baseline strategy.

The backtest reports:
- trades
- wins / losses / expired
- win rate
- profit factor
- expectancy in R
- total net R
- maximum drawdown in R
- LONG vs SHORT performance
- recent trades

Costs are included through configurable round-trip fees and slippage.

Default assumptions:
- fees: 11 bps round trip
- slippage: 4 bps round trip
- target: 1.5R
- maximum hold: 4 candles
- ambiguous same-candle target/stop: STOP FIRST

This baseline does **not** recreate historical cross-exchange order flow or live CVD.
It validates the replay infrastructure and a technical subset only.

### Walk-forward / holdout baseline
`GET /api/v1/validation/walk-forward?interval=15&candles=1000`

The first 70% of candles are treated as training history.
The final 30% are held out for a basic out-of-sample check.

Baseline pass requires:
- at least 20 held-out trades
- positive expectancy
- profit factor > 1.05

This is not proof of future profitability. It is a minimum sanity check.

### Signal cooldown / deduplication
Paper candidates are no longer blindly saved every API call.

Default:
- same direction cooldown: 20 minutes
- duplicate price tolerance: 0.20%

If the same directional signal is repeated inside the cooldown with little price
movement, FIND suppresses it.

Blocker:
`SIGNAL_COOLDOWN_DUPLICATE`

### Strategy versioning
Every stored candidate now includes:

`strategy_version = FIND-V5-1`

This matters because performance from different rule sets should never be mixed.

## Existing V4 quality layers retained

- Bybit rolling WebSocket CVD
- Bybit + Binance Futures + Coinbase Spot consensus
- event-risk blocker
- automatic TP / SL / expiry evaluation
- performance API
- Paper Mode

## Important limitation

Bybit's REST kline endpoint supplies historical candles, while recent public trades
and the live WebSocket provide current trade flow. Therefore V5's candle backtest
does not pretend to reconstruct historical CVD, order-book imbalance, or
cross-exchange consensus from candle data alone.

For a full FIND backtest we need to build our own historical microstructure archive
or source archived trade/order-book datasets.

## Main endpoints

- `/api/v1/signal`
- `/api/v1/performance`
- `/api/v1/backtest`
- `/api/v1/validation/walk-forward`
- `/api/v1/live/cvd`
- `/api/v1/events/risk`
- `/api/v1/signals/recent`

## Next milestone: V6

V6 should start the first Android-facing product layer:

- stable dashboard API
- compact market-status object
- FIND score cards
- signal history
- performance summary
- notification-ready signal object
- Android app shell matching AMP TRADE CORE
- NO TRADE / SETUP FORMING / PAPER OPPORTUNITY UI


## V6 Android dashboard endpoint

`GET /api/v1/dashboard`

This endpoint is intentionally compact and Android-facing. It aggregates:
- BTC price and 24h change
- market bias
- FIND long/short scores
- setup state and blockers
- 5m live CVD
- Bybit orderflow
- Bybit/Binance/Coinbase consensus
- event risk
- paper performance
- recent paper signals

The Android client can refresh this one endpoint rather than orchestrating many requests.
