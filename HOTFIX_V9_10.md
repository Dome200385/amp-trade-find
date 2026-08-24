# AMP TRADE FIND V9.10 — Frozen Forward Selection

V9.10 converts the completed V9.9 fresh forward cohort into a deliberately conservative, frozen selection layer.

- Strategy: `FIND-V9.10-1`
- Source cohort: `FIND-V9.9-1` only
- Source must contain at least 50 resolved trades before V9.10 captures anything.
- Selection evidence is built from direction, regime, volatility and cross-market marginals.
- Each feature value needs >=10 resolved V9.9 samples to influence selection.
- A candidate is rejected if any matched supported feature is statistically weak under the configured rules.
- A candidate needs >=2 independently supported feature votes to enter V9.10.
- V9.10 results never feed back into the selector.
- New V9.10 forward cohort starts at 0/50 after deployment.
- Paper mode remains enabled; no live execution was added.
