# AMP TRADE FIND V8.1 – REST fallback hotfix

Reason:
Render receives HTTP 403 from Bybit REST endpoints while the Bybit public WebSocket
continues to work.

V8.1 does not bypass the restriction.

Market-data source priority:
1. Bybit REST
2. Binance USD-M Futures REST
3. Coinbase Exchange public spot REST

The live Bybit WebSocket CVD remains active independently.

Also updated:
- current-price outcome evaluation uses the same fallback chain
- backtest / validation candle history uses the same fallback chain
- cross-exchange consensus marks Bybit REST unavailable rather than failing the request
- dashboard reports `primary_source`, `source_degraded`, and `source_errors`
- new endpoint: `/api/v1/sources/status`

Expected Render result in the current environment:
`primary_source = BINANCE`
with Bybit listed in `source_errors`.

A degraded source is visible to the signal engine and added as a blocker/status marker.
