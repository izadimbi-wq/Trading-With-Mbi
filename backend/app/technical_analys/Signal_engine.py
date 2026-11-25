
from math import isfinite


def _valid_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and isfinite(value)
    )


def generate_signal(indicators):
    """
    Generate BUY, SELL or NO TRADE from calculated indicators.

    This function does not execute trading orders.
    """

    if not isinstance(indicators, dict):
        raise ValueError("Indicators must be a dictionary.")

    required_keys = {
        "ema",
        "rsi",
        "atr",
        "macd",
        "ichimoku"
    }

    if not required_keys.issubset(indicators):
        raise ValueError("Required indicators are missing.")

    ema_data = indicators["ema"]
    rsi_data = indicators["rsi"]
    atr_data = indicators["atr"]
    macd_data = indicators["macd"]
    ichimoku_data = indicators["ichimoku"]

    if not all(
        isinstance(item, dict)
        for item in (
            ema_data,
            rsi_data,
            macd_data,
            ichimoku_data
        )
    ):
        raise ValueError("Invalid indicator data structure.")

    ema_fast = ema_data.get("fast")
    ema_slow = ema_data.get("slow")
    rsi_value = rsi_data.get("value")
    atr_value = atr_data.get("value")
    macd_line = macd_data.get("macd")
    signal_line = macd_data.get("signal")

    price_vs_cloud = ichimoku_data.get(
        "price_vs_cloud"
    )

    tenkan_kijun_bias = ichimoku_data.get(
        "tenkan_kijun_bias"
    )

    numeric_values = (
        ema_fast,
        ema_slow,
        rsi_value,
        atr_value,
        macd_line,
        signal_line
    )

    if not all(
        _valid_number(value)
        for value in numeric_values
    ):
        return {
            "signal": "NO TRADE",
            "status": "INVALID_INDICATOR_DATA",
            "reason": "One or more indicator values are invalid.",
            "buy_confirmations": [],
            "sell_confirmations": []
        }

    if (
        ema_fast <= 0
        or ema_slow <= 0
        or atr_value <= 0
        or not 0 <= rsi_value <= 100
    ):
        return {
            "signal": "NO TRADE",
            "status": "INVALID_INDICATOR_DATA",
            "reason": "Indicator values are outside valid ranges.",
            "buy_confirmations": [],
            "sell_confirmations": []
        }

    if price_vs_cloud not in (
        "ABOVE",
        "BELOW",
        "INSIDE"
    ):
        return {
            "signal": "NO TRADE",
            "status": "INSUFFICIENT_DATA",
            "reason": "Current Ichimoku cloud position is unavailable.",
            "buy_confirmations": [],
            "sell_confirmations": []
        }

    if tenkan_kijun_bias not in (
        "BULLISH",
        "BEARISH",
        "NEUTRAL"
    ):
        return {
            "signal": "NO TRADE",
            "status": "INVALID_INDICATOR_DATA",
            "reason": "Invalid Ichimoku Tenkan/Kijun bias.",
            "buy_confirmations": [],
            "sell_confirmations": []
        }

    buy_confirmations = []
    sell_confirmations = []

    if ema_fast > ema_slow:
        buy_confirmations.append("EMA_BULLISH")
    elif ema_fast < ema_slow:
        sell_confirmations.append("EMA_BEARISH")

    if price_vs_cloud == "ABOVE":
        buy_confirmations.append("PRICE_ABOVE_CLOUD")
    elif price_vs_cloud == "BELOW":
        sell_confirmations.append("PRICE_BELOW_CLOUD")

    if tenkan_kijun_bias == "BULLISH":
        buy_confirmations.append("TENKAN_ABOVE_KIJUN")
    elif tenkan_kijun_bias == "BEARISH":
        sell_confirmations.append("TENKAN_BELOW_KIJUN")

    if macd_line > signal_line:
        buy_confirmations.append("MACD_BULLISH")
    elif macd_line < signal_line:
        sell_confirmations.append("MACD_BEARISH")

    if 50 < rsi_value < 70:
        buy_confirmations.append("RSI_BULLISH")
    elif 30 < rsi_value < 50:
        sell_confirmations.append("RSI_BEARISH")

    required_confirmations = 5

    if len(buy_confirmations) == required_confirmations:
        signal = "BUY"
        status = "SIGNAL_GENERATED"
        reason = "All buy conditions are confirmed."

    elif len(sell_confirmations) == required_confirmations:
        signal = "SELL"
        status = "SIGNAL_GENERATED"
        reason = "All sell conditions are confirmed."

    else:
        signal = "NO TRADE"
        status = "NO_VALID_SETUP"
        reason = (
            "Not all required conditions agree "
            "in the same direction."
        )

    return {
        "signal": signal,
        "status": status,
        "reason": reason,
        "buy_confirmations": buy_confirmations,
        "sell_confirmations": sell_confirmations,
        "required_confirmations": required_confirmations,
        "atr": atr_value,
        "rsi": rsi_value,
        "note": (
            "Analytical signal only. No trading order "
            "is executed. Chikou is not used as a "
            "signal condition."
        )
    }
