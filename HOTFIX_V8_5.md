# AMP TRADE FIND V8.5 – Signal Validation Engine

V8.5 turns FIND into a measurable paper-validation system.

Captured setups:
- WATCH
- SETUP_FORMING
- READY
- PAPER_SIGNAL

Capture requirements:
- LONG or SHORT directional bias
- score >= 65
- quality MEDIUM or HIGH
- valid entry plan

Each setup stores:
- strategy version
- direction
- score and quality grade
- entry zone / entry center
- stop / TP1 / TP2 / RR
- primary data source
- available venues
- live CVD direction / delta
- capture hour UTC
- full signal + market snapshot

Lifecycle:
WAITING_ENTRY
-> ACTIVE
-> TP1 / TP2 / STOPPED / EXPIRED

or:
WAITING_ENTRY
-> MISSED_ENTRY

Automatic evaluator runs every 15 seconds.

Metrics:
- captured
- entered
- resolved
- wins / losses
- missed entries
- win rate
- profit factor
- expectancy in R
- average MFE in R
- average MAE in R

Breakdowns:
- LONG vs SHORT
- quality grade
- score bucket
- hour UTC

Validation gates default to:
- >= 200 resolved samples
- profit factor >= 1.15
- expectancy >= +0.05R

Endpoints:
GET  /api/v1/validation/report
GET  /api/v1/validation/setups
POST /api/v1/validation/evaluate
POST /api/v1/validation/capture-now

PAPER_MODE remains active.
Passing the statistical gates will not automatically enable live execution or push alerts.
