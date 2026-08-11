# V9.3.1 Hotfix

Fixes:
- Validation Intelligence now reads the existing validation_setups schema defensively.
- TP1, TP2, STOPPED and EXPIRED are treated as resolved outcomes.
- ACTIVE remains unresolved.
- Legacy records without grade/confidence remain included under LEGACY.
- If older records do not contain close_r, R is reconstructed from outcome and stored R:R.
- API display/version aligned to 0.9.3.
- Strategy version FIND-V9.3.1.

Expected after deployment with the current database:
- Resolved sample should no longer incorrectly show 0 when TP1/STOPPED records exist.
- Best direction/grade/confidence and leaderboard can populate from legacy samples.
