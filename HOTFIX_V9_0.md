# AMP TRADE FIND V9.0 – Monitoring Dashboard

New browser dashboard:
GET /monitor

New dashboard data endpoint:
GET /api/v1/monitoring

Dashboard shows:
- BTC price + primary source
- state + directional bias
- LONG / SHORT score
- signal quality + live CVD
- validation progress toward 200 resolved samples
- captured / active / waiting setups
- collector health + last cycle
- 24h collector runs
- venue availability for Bybit, Binance, OKX, Kraken, Coinbase
- taker delta and orderbook imbalance by venue
- validation win rate, profit factor, expectancy
- current blockers and warnings

Auto refresh:
10 seconds

The dashboard is read-only.
PAPER_MODE remains enabled.
No trade execution is added.
