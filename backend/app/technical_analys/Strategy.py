from math import isfinite

SUPPORTED_SYMBOLS = {
    "XAUUSD",
    "EURUSD",
    "XAGUSD"
}

SUPPORTED_TIMEFRAMES = {
    "M1",
    "M5",
    "M15",
    "M30",
    "H1",
    "H4",
    "D1"
}

DEFAULT_SETTINGS = {
    "ema_fast": 20,
    "ema_slow": 50,
    "rsi_period": 14,
    "atr_period": 14,
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,
    "ichimoku_tenkan": 9,
    "ichimoku_kijun": 26,
    "ichimoku_senkou_b": 52
}


def validate_market_input(
    symbol,
    timeframe,
    candles
):
    symbol = str(symbol).upper()
    timeframe = str(timeframe).upper()

    if symbol not in SUPPORTED_SYMBOLS:
        raise ValueError("Unsupported trading symbol.")

    if timeframe not in SUPPORTED_TIMEFRAMES:
        raise ValueError("Unsupported timeframe.")

    if not isinstance(candles, list):
        raise ValueError("Candles must be a list.")

    if not candles:
        raise ValueError("Candles cannot be empty.")

    required_fields = {
        "open",
        "high",
        "low",
        "close"
    }

    for index, candle in enumerate(candles):
        if not isinstance(candle, dict):
            raise ValueError(
                f"Invalid candle at index {index}."
            )

        if not required_fields.issubset(candle):
            raise ValueError(
                f"Incomplete candle at index {index}."
            )

        for field in required_fields:
            value = candle[field]

            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not isfinite(value)
                or value <= 0
            ):
                raise ValueError(
                    f"Invalid {field} at index {index}."
                )

        if candle["high"] < max(
            candle["open"],
            candle["close"]
        ):
            raise ValueError(
                f"Invalid high at index {index}."
            )

        if candle["low"] > min(
            candle["open"],
            candle["close"]
        ):
            raise ValueError(
                f"Invalid low at index {index}."
            )

        if candle["high"] < candle["low"]:
            raise ValueError(
                f"Invalid OHLC range at index {index}."
            )

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "candles": candles
    }
