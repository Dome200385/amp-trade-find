# AMP TRADE FIND V8.6 – Validation Route Fix

Purpose:
- fix missing /api/v1/validation/... routes
- make API and strategy versions consistent

Expected version:
- api_version: 0.8.6
- strategy_version: FIND-V8.5-1

New verification endpoint:
GET /api/v1/version

Validation endpoints:
GET  /api/v1/validation/report
GET  /api/v1/validation/setups
POST /api/v1/validation/capture-now

After deploy, test in this order:
1. /api/v1/version
2. /api/v1/validation/report
3. /api/v1/validation/capture-now

PAPER_MODE remains active.
