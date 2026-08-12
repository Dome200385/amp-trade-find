# AMP TRADE FIND V9.6.1 – Learning Funnel

No trading thresholds are changed.

New persistent funnel telemetry:
- every collector cycle is classified
- STRICT_CAPTURE
- LEARNING_CAPTURE
- STRICT_CANDIDATE
- LEARNING_CANDIDATE
- REJECTED_NOISE

Stored for every scan:
- state
- direction
- LONG/SHORT score
- confidence
- quality
- strict rejection reason
- learning rejection reason
- capture mode

New endpoint:
GET /api/v1/learning/funnel?hours=24

Dashboard:
Learning Funnel · 24h
- scans
- candidates
- candidate rate
- learning captures
- strict captures
- rejected noise
- top learning rejection reason

Purpose:
Before lowering any threshold, FIND can now show exactly where potential validation samples are being filtered out.

PAPER_MODE remains enabled.
No live trade execution.
