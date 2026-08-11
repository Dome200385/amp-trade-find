# AMP TRADE FIND V9.5.2 – Unified Data Source Fix

No trading rules changed.

The monitoring modules now share the same sources:

Validation source:
- Lifecycle Health
- Validation Intelligence
- Learning Readiness
all use app.services.unified_validation.

Venue source:
- Market Venues table
- Data Health
both use the same normalized_venues object from monitoring.py.

Expected current values with the existing persistent DB:
- Validation Intelligence Resolved sample: 2
- Learning Readiness: INSUFFICIENT, Resolved 2
- Lifecycle Health: TRACKING, Active 1, Resolved 2
- Data Health: 3/3 when OKX, Kraken and Coinbase are live

Strategy:
FIND-V9.5.2

API:
0.9.5

PAPER_MODE remains enabled.
