# AMP TRADE FIND V9.6.2 – Observability & Data Integrity

No trading thresholds or signal rules were changed.

- TP1 remains the primary resolved validation outcome, preserving historical comparability.
- After TP1, the lifecycle observer continues tracking TP2 or a later stop via separate milestone fields.
- Existing validation rows are migrated in-place; no validation reset is performed.
- Learning Funnel records capture-stage rejection reasons and exposes candidate capture failures.
- Monitoring uses cross_exchange as the canonical venue map.
- Data Health separates primary price feed, REST bundle and cross-exchange orderflow capabilities.
