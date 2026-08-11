# AMP TRADE FIND — V9.3.2 Hotfix

## Fix
The monitoring payload now includes `intelligence`, using the same `build_intelligence()` result already exposed by `/api/v1/validation/intelligence`.

This fixes the dashboard showing `Resolved sample = 0` and an empty Best Setup Types table even while the validation report already contains resolved TP1/TP2/STOPPED/EXPIRED setups.

No trading, scoring, entry, risk, collector, persistence, or outcome logic was changed.

Version: API 0.9.4 / FIND-V9.3.2
