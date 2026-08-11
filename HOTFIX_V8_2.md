# AMP TRADE FIND V8.2 – Multi-Venue

Adds OKX BTC-USDT-SWAP and Kraken XBT/USD. Fallback: Bybit -> Binance -> OKX -> Kraken -> Coinbase. Consensus can use all five venues. At least two independent venues must confirm direction. PAPER_MODE stays enabled. Test /api/v1/sources/status and /api/v1/dashboard after deployment; desired available_venues >= 2.
