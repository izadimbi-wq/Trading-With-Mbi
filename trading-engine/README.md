# Trading Engine

This module is intentionally a domain scaffold. No strategy is represented as profitable or
validated. Implement indicators against timestamped OHLC data and test for look-ahead bias.

Suggested pipeline:
1. Validate feed timestamps and symbol metadata.
2. Build candles from broker Bid/Ask ticks.
3. Calculate EMA 20/50/200, Ichimoku, RSI, MACD and ATR.
4. Evaluate multi-timeframe context.
5. Return BUY / SELL / NO_TRADE with reasons and expiry.
6. Pass candidate trades through risk-management; risk rejection overrides any signal.
