from app.services.backtest import summarize, Trade

def test_summary_profit_factor():
    trades = [
        Trade("LONG", "a", "b", 100, 102, 99, 102, 1.5, 1.4, "TP1"),
        Trade("SHORT", "c", "d", 100, 101, 101, 98, -1.0, -1.1, "STOPPED"),
    ]
    s = summarize(trades, 1.1)
    assert s["trades"] == 2
    assert s["profit_factor"] is not None
