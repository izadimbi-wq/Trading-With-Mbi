
from math import isfinite

from technical_analysis.indicators import (
    ema,
    rsi,
    atr,
    macd,
    ichimoku
)


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
    "ichimoku_senkou_b": 52,
    "ichimoku_displacement": 26
}


def validate_market_input(symbol, timeframe, candles):
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

        if candle.get("isOpen") is True:
            raise ValueError(
                "Open candles must be excluded from analysis."
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


def calculate_indicators(candles):
    if not isinstance(candles, list) or not candles:
        raise ValueError("Candles must be a non-empty list.")

    settings = DEFAULT_SETTINGS

    closes = [candle["close"] for candle in candles]
    highs = [candle["high"] for candle in candles]
    lows = [candle["low"] for candle in candles]

    required_candles = max(
        settings["ema_slow"],
        settings["rsi_period"] + 1,
        settings["atr_period"] + 1,
        settings["macd_slow"] + settings["macd_signal"] - 1,
        settings["ichimoku_senkou_b"]
        + settings["ichimoku_displacement"]
    )

    if len(candles) < required_candles:
        return {
            "status": "INSUFFICIENT_DATA",
            "required_candles": required_candles,
            "available_candles": len(candles)
        }

    ema_fast = ema(
        closes,
        settings["ema_fast"]
    )

    ema_slow = ema(
        closes,
        settings["ema_slow"]
    )

    rsi_value = rsi(
        closes,
        settings["rsi_period"]
    )

    atr_value = atr(
        highs,
        lows,
        closes,
        settings["atr_period"]
    )

    macd_value = macd(
        closes,
        settings["macd_fast"],
        settings["macd_slow"],
        settings["macd_signal"]
    )

    ichimoku_value = ichimoku(
        highs,
        lows,
        closes=closes,
        tenkan_period=settings["ichimoku_tenkan"],
        kijun_period=settings["ichimoku_kijun"],
        senkou_b_period=settings["ichimoku_senkou_b"],
        displacement=settings["ichimoku_displacement"]
    )

    return {
        "status": "CALCULATED",
        "candles_used": len(candles),
        "indicators": {
            "ema": {
                "fast_period": settings["ema_fast"],
                "fast": ema_fast,
                "slow_period": settings["ema_slow"],
                "slow": ema_slow
            },
            "rsi": {
                "period": settings["rsi_period"],
                "value": rsi_value
            },
            "atr": {
                "period": settings["atr_period"],
                "value": atr_value
            },
            "macd": macd_value,
            "ichimoku": ichimoku_value
        }
    }


def analyze_market(symbol, timeframe, candles):
    validated = validate_market_input(
        symbol,
        timeframe,
        candles
    )

    result = calculate_indicators(
        validated["candles"]
    )

    result["symbol"] = validated["symbol"]
    result["timeframe"] = validated["timeframe"]
    result["signal"] = "NOT_EVALUATED"

    result["note"] = (
        "Indicators calculated without generating trading signals. "
        "Candles must be closed and ordered from oldest to newest. "
        "At least 78 candles are required for the current Ichimoku cloud."
    )

    return result
