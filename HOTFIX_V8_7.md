# AMP TRADE FIND V8.7 – Automatic Validation Engine

V8.7 removes the need to press capture-now manually.

Automatic loop:
1. fetch market snapshot
2. calculate FIND signal
3. apply validation capture policy
4. capture qualified setup
5. evaluate all waiting/active validation setups
6. repeat

Default scan interval:
30 seconds

Automatic capture policy:
- state >= SETUP_FORMING
- directional bias LONG or SHORT
- quality MEDIUM or HIGH
- cross-market confirmation required
- entry plan required
- duplicate/cooldown protection retained

Existing outcome lifecycle:
WAITING_ENTRY
-> ACTIVE
-> TP1 / TP2 / STOPPED / EXPIRED

or:
WAITING_ENTRY
-> MISSED_ENTRY

New endpoints:
GET  /api/v1/validation/auto/status
POST /api/v1/validation/auto/run
GET  /api/v1/version

Recommended post-deploy checks:
1. /api/v1/version
2. /api/v1/validation/auto/status
3. /api/v1/validation/report
4. /api/v1/validation/setups

PAPER_MODE remains enabled.
No live trading execution is added.
