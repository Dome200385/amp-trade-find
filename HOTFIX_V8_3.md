# AMP TRADE FIND V8.3 – Signal Quality Upgrade

Main changes:

1. A valid fallback source such as OKX is no longer a signal blocker.
   Failed Bybit/Binance REST connections are reported as warnings/status only.

2. Spot and derivatives are evaluated separately.

Derivatives:
- Bybit Futures
- Binance Futures
- OKX Swap

Spot:
- Kraken
- Coinbase

3. HIGH quality requires agreement across market types:
- at least one derivatives venue confirming the direction
- at least one spot venue confirming the same direction
- at least 3 available venues total
- no opposing confirming venue inside either group

4. A paper LONG/SHORT candidate additionally requires:
- HIGH signal quality
- matching 5M live Bybit CVD
- matching 5M timing
- no high-impact event block
- score >= configured signal threshold

5. Conflicts become explicit blockers:
- SPOT_DERIVATIVES_CONFLICT
- CROSS_MARKET_CONFIRMATION_MISSING
- LOW_SIGNAL_QUALITY

6. Source failures are warnings, not trade blockers:
- PRIMARY_SOURCE_FALLBACK_OKX
- BYBIT_REST_UNAVAILABLE
- BINANCE_REST_UNAVAILABLE

PAPER_MODE and BACKTEST_NOT_VALIDATED remain active.

After deployment:
- /api/v1/sources/status
- /api/v1/dashboard

Look inside:
signal.quality
signal.blockers
signal.warnings
