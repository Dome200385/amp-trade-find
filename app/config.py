from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "AMP TRADE FIND"
    app_version: str = "0.8.0"

    bybit_base_url: str = "https://api.bybit.com"
    bybit_ws_linear_url: str = "wss://stream.bybit.com/v5/public/linear"
    binance_futures_base_url: str = "https://fapi.binance.com"
    coinbase_exchange_base_url: str = "https://api.exchange.coinbase.com"

    symbol: str = "BTCUSDT"
    coinbase_product: str = "BTC-USD"
    category: str = "linear"

    signal_threshold: int = 80
    setup_threshold: int = 70
    watch_threshold: int = 55

    database_path: str = "amp_find_signals.db"
    event_file: str = "data/high_impact_events.json"

    paper_mode: bool = True
    min_validated_samples: int = 200
    max_signal_validity_minutes: int = 15

    strategy_version: str = "FIND-V8-1"
    signal_cooldown_minutes: int = 20
    signal_dedupe_price_pct: float = 0.20

    backtest_fee_bps_round_trip: float = 11.0
    backtest_slippage_bps_round_trip: float = 4.0
    backtest_default_candles: int = 1000

    notification_min_score: int = 80
    notification_cooldown_minutes: int = 20

    public_base_url: str = ""
    firebase_service_account_json: str = ""
    firebase_enabled: bool = False
    push_topic: str = "amp_find_signals"
    admin_api_key: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()
