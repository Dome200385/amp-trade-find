# AMP TRADE FIND V9.9-1 — Forward Diagnostic Filter

V9.8 failed its frozen 50-trade forward test (22% win rate, PF 0.42, -0.45R expectancy).
V9.9 uses those V9.8 forward trades only as diagnostic evidence.

Conservative filter rules:
- a bucket needs at least 8 V9.8 forward-resolved samples;
- expectancy must be <= -0.20R;
- additionally PF < 0.80 OR win rate < 35%;
- live match requires direction + market regime + volatility + cross-market consensus;
- blocked setups do not enter STRICT/LEARNING validation but remain eligible for shadow Observation Learning;
- no auto-retraining and no self-modifying thresholds.

A fresh FIND-V9.9-1 0/50 cohort measures new out-of-sample performance. V9.8 trades never count toward it.
PAPER_MODE remains enabled. No live execution.
