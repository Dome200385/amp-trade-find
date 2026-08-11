# AMP TRADE FIND V9.5.1 – Health Integration Fix

Fixes only monitoring/integration. Trading logic is unchanged.

Data Health:
- reads venues from cross_exchange, orderflow.venues, or named venue payloads
- counts OKX/Kraken/Coinbase correctly even when payload shape differs
- calculates collector age defensively

Lifecycle Health:
- reads the actual validation_setups schema
- supports outcome or status column
- correctly counts WAITING_ENTRY, ACTIVE, TP1, TP2, STOPPED, EXPIRED, MISSED_ENTRY

Learning Readiness:
- uses Validation Intelligence resolved count as source of truth
- therefore matches the same resolved sample count shown by the intelligence panel

Expected current dashboard:
- Data Health: 3/3 live venues if OKX/Kraken/Coinbase are live
- Learning Readiness: INSUFFICIENT, Resolved 2
- Lifecycle Health: TRACKING, Active 1, Resolved 2

Version:
API 0.9.5
Strategy FIND-V9.5.1

No trading rules changed.
PAPER_MODE remains enabled.
