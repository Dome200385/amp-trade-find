from app.services.backtest import run_backtest, summarize

def walk_forward(rows, train_ratio=0.70):
    n = len(rows)
    split = max(100, int(n * train_ratio))
    train_rows = rows[:split]
    test_rows = rows[max(0, split - 60):]

    train_trades, train_dd = run_backtest(train_rows)
    test_trades, test_dd = run_backtest(test_rows)

    return {
        "method": "single holdout walk-forward baseline",
        "train_candles": len(train_rows),
        "test_candles": len(test_rows),
        "train": summarize(train_trades, train_dd),
        "test": summarize(test_trades, test_dd),
        "passed_baseline": (
            len(test_trades) >= 20
            and (summarize(test_trades, test_dd)["expectancy_r"] or 0) > 0
            and (summarize(test_trades, test_dd)["profit_factor"] or 0) > 1.05
        ),
        "note": "This is a baseline validation harness, not proof of future profitability."
    }
