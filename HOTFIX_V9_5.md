# AMP TRADE FIND V9.5 – Validation Engine & Data Health

V9.5 keeps signal rules unchanged.

New:
- Data Health monitoring
- Collector staleness detection
- Venue coverage warnings
- Learning Readiness levels
- Validation lifecycle health
- New dashboard cards

Learning readiness:
- INSUFFICIENT: <10 resolved
- EARLY: 10–29
- USABLE: 30–99
- STRONG: 100+

New endpoints:
GET /api/v1/learning/readiness
GET /api/v1/validation/lifecycle

Monitoring payload now includes:
- data_health
- learning_readiness
- lifecycle_health

PAPER_MODE remains enabled.
No live execution.
