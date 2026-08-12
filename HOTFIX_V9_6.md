# AMP TRADE FIND V9.6 — Validation Acceleration

V9.6 separates strict trade qualification from broader paper-learning capture.

- READY/PAPER_SIGNAL trading rules are unchanged.
- Learning capture can store WATCH+ candidates from score 45, including LOW quality.
- Cross-market confirmation is not required for learning candidates.
- Every learning row is tagged `capture_tier=LEARNING` and stores the strict rejection reason.
- Existing lifecycle evaluation resolves learning candidates exactly like strict paper candidates.
- Monitoring exposes the active acceleration policy.

Goal: create enough labelled outcomes to learn which blockers and market conditions actually add predictive value, without weakening actionable trade signals.
