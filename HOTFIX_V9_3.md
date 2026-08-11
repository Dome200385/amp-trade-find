# AMP TRADE FIND V9.3 – Validation Intelligence

V9.3 focuses on understanding which setup types actually work.

New intelligence dimensions:
- LONG vs SHORT
- A/B/C/UNRATED/LEGACY setup grade
- HIGH/MEDIUM/LOW quality
- confidence buckets
- score buckets
- UTC hour

Metrics per group:
- captured
- resolved
- wins / losses
- win rate
- profit factor
- expectancy in R
- average confidence
- TP1 rate
- TP2 rate
- stop rate

New combination leaderboard:
direction + setup grade + confidence bucket

The leaderboard is sample-weighted so one lucky trade does not rank like a mature group.

New endpoint:
GET /api/v1/validation/intelligence

Dashboard adds:
- best direction
- best grade
- best confidence bucket
- resolved-sample count
- best setup types table

Existing validation data is preserved.

Version:
API 0.9.3
Strategy FIND-V9.3-1

PAPER_MODE remains enabled.
No live trade execution is added.
