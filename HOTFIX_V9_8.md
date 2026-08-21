# AMP TRADE FIND V9.8-1 — Frozen Regime Prior + Forward Test

- Historical validation is frozen once at first V9.8 startup.
- Only buckets with >=20 resolved samples can affect scoring.
- Adjustment is bounded to +/-8 points.
- A frozen prior cannot create a direction from a neutral raw signal.
- V9.8 outcomes are tracked separately as an out-of-sample forward cohort.
- Forward-test target: 50 resolved samples.
- STRICT / LEARNING / OBSERVATION remain in place.
- PAPER_MODE remains enabled; no live trade execution.
