# AMP TRADE FIND V8.9 – Persistent Collector

Every 30 seconds FIND now:
1. evaluates existing validation setups
2. fetches multi-venue BTC market data
3. calculates state/scores/quality
4. applies strict capture rules
5. stores qualified setups
6. stores collector telemetry

Capture remains strict:
- SETUP_FORMING / READY / PAPER_SIGNAL
- LONG or SHORT bias
- MEDIUM/HIGH quality
- cross-market confirmation
- valid entry plan
- existing duplicate/cooldown protection
- max 12 waiting/active setups

New persistent table: collector_runs

New endpoints:
GET /api/v1/collector/status
POST /api/v1/collector/run
GET /api/v1/collector/stats?hours=24

The collector reports progress toward 200 resolved validation samples.

PAPER_MODE remains enabled. No live trade execution is added.
