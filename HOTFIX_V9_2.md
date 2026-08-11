# AMP TRADE FIND V9.2 – Adaptive Signal Quality

V9.2 adds a second quality layer above the raw LONG/SHORT score.

New live metrics:
- Confidence 0–100%
- Setup Grade A / B / C / UNRATED
- Explicit strengths
- Explicit contradictions

Confidence combines:
- directional score
- score separation
- spot + derivatives confirmation
- existing quality grade
- live 5M CVD
- 5M timing
- 1H + 15M trend agreement
- venue availability
- spot/derivatives conflicts

Grade logic is intentionally strict:
- A: strongest multi-source alignment
- B: good setup with weaker confirmation somewhere
- C: directional setup, moderate confirmation
- UNRATED: insufficient confirmation

Validation database migration:
Existing validation_setups are preserved.
Two nullable columns are added automatically:
- setup_grade
- confidence_pct

New validation analytics:
- by_setup_grade
- by_confidence_bucket
- TP1 rate
- TP2 rate
- stop rate
- LONG vs SHORT remains available
- HIGH/MEDIUM quality analysis remains available

Dashboard:
- live confidence
- live setup grade
- opportunity score now includes grade + confidence
- recent setups include grade + confidence
- validation metrics include TP1 / TP2 / Stop rates

Persistence remains:
 /var/data/amp_trade_find.db

PAPER_MODE remains active.
No automatic trade execution is added.
