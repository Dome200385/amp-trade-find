# AMP TRADE FIND V8.4 – Entry Engine & Signal State Machine

V8.4 introduces a proper signal lifecycle:

NO_TRADE
-> WATCH
-> SETUP_FORMING
-> READY
-> PAPER_SIGNAL

A PAPER_SIGNAL is only created when:
- directional score >= 80
- signal quality is HIGH
- spot + derivatives confirm same direction
- live 5M CVD confirms direction
- 5M timing confirms direction
- no high-impact event block
- entry plan is valid
- current price is inside the calculated entry zone

New Entry Engine:
- entry_low / entry_high
- entry_center
- stop
- TP1
- TP2
- RR1 / RR2
- invalidation text
- validity window
- entry_now flag

New endpoint:
GET /api/v1/state

This exposes the state machine without needing to inspect the full dashboard.

Important:
PAPER_MODE and BACKTEST_NOT_VALIDATED remain active.
V8.4 still does not enable production push trading alerts.
