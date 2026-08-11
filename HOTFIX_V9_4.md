# AMP TRADE FIND V9.4 – Market Regime Learning

V9.4 does NOT change entry thresholds.

It adds contextual feature capture for every newly stored validation setup:
- market regime
- volatility bucket
- 1H trend
- 15M trend
- VWAP bias
- RSI detail
- 5M timing detail
- cross-market consensus
- spot/derivatives conflict
- live CVD direction and %
- venue count
- primary data source
- source degradation
- spread
- 24h change
- funding rate
- primary taker delta
- primary orderbook imbalance
- UTC hour + weekday
- raw scores
- confidence
- setup grade

Persistent DB migration:
validation_setups gains nullable features_json.
Existing records are preserved and remain LEGACY for regime analysis.

New endpoint:
GET /api/v1/validation/regimes

Dashboard:
- Market Regime Learning card
- Best Market Conditions table
- best regime / volatility / cross-market condition
- feature sample count

This allows future optimization based on conditions rather than intuition.

PAPER_MODE remains active.
No live trade execution.
