
from math import isfinite


def _validate_prices(values, name="prices"):
    if not isinstance(values, (list, tuple)):
        raise ValueError(f"{name} must be a list or tuple.")

    if not values:
        raise ValueError(f"{name} cannot be empty.")

    result = []

    for value in values:
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not isfinite(value)
            or value <= 0
        ):
            raise ValueError(f"Invalid value in {name}.")

        result.append(float(value))

    return result


def ema(prices, period):
    prices = _validate_prices(prices)

    if not isinstance(period, int) or isinstance(period, bool) or period < 1:
        raise ValueError("Period must be a positive integer.")

    if len(prices) < period:
        return None

    multiplier = 2.0 / (period + 1)

    result = sum(prices[:period]) / period

    for price in prices[period:]:
        result = (
            price * multiplier
            + result * (1.0 - multiplier)
        )

    return result


def rsi(prices, period=14):
    prices = _validate_prices(prices)

    if not isinstance(period, int) or isinstance(period, bool) or period < 1:
        raise ValueError("Period must be a positive integer.")

    if len(prices) < period + 1:
        return None

    gains = []
    losses = []

    for index in range(1, len(prices)):
        change = prices[index] - prices[index - 1]

        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))

    average_gain = sum(gains[:period]) / period
    average_loss = sum(losses[:period]) / period

    for index in range(period, len(gains)):
        average_gain = (
            average_gain * (period - 1) + gains[index]
        ) / period

        average_loss = (
            average_loss * (period - 1) + losses[index]
        ) / period

    if average_loss == 0:
        return 100.0 if average_gain > 0 else 50.0

    if average_gain == 0:
        return 0.0

    relative_strength = average_gain / average_loss

    return 100.0 - (100.0 / (1.0 + relative_strength))


def atr(highs, lows, closes, period=14):
    highs = _validate_prices(highs, "highs")
    lows = _validate_prices(lows, "lows")
    closes = _validate_prices(closes, "closes")

    if not isinstance(period, int) or isinstance(period, bool) or period < 1:
        raise ValueError("Period must be a positive integer.")

    if not (len(highs) == len(lows) == len(closes)):
        raise ValueError("OHLC arrays must have equal lengths.")

    if len(closes) < period + 1:
        return None

    true_ranges = []

    for index in range(1, len(closes)):
        if highs[index] < lows[index]:
            raise ValueError("High cannot be lower than low.")

        if (
            highs[index] < max(closes[index], closes[index - 1])
            or lows[index] > min(closes[index], closes[index - 1])
        ):
            raise ValueError("Inconsistent OHLC values.")

        true_range = max(
            highs[index] - lows[index],
            abs(highs[index] - closes[index - 1]),
            abs(lows[index] - closes[index - 1])
        )

        true_ranges.append(true_range)

    result = sum(true_ranges[:period]) / period

    for value in true_ranges[period:]:
        result = (
            result * (period - 1) + value
        ) / period

    return result

def macd(prices, fast=12, slow=26, signal=9):
    prices = _validate_prices(prices)

    periods = (fast, slow, signal)

    if any(
        not isinstance(p, int) or isinstance(p, bool) or p < 1
        for p in periods
    ):
        raise ValueError("MACD periods must be positive integers.")

    if fast >= slow:
        raise ValueError("Fast period must be smaller than slow period.")

    if len(prices) < slow + signal - 1:
        return None

    fast_multiplier = 2.0 / (fast + 1)
    slow_multiplier = 2.0 / (slow + 1)

    fast_ema = sum(prices[:fast]) / fast
    slow_ema = sum(prices[:slow]) / slow

    macd_values = []

    for index in range(slow, len(prices)):
        fast_ema = (
            prices[index] * fast_multiplier
            + fast_ema * (1 - fast_multiplier)
        )

        slow_ema = (
            prices[index] * slow_multiplier
            + slow_ema * (1 - slow_multiplier)
        )

        macd_values.append(fast_ema - slow_ema)

    if len(macd_values) < signal:
        return None

    signal_line = ema(macd_values, signal)

    return {
        "macd": macd_values[-1],
        "signal": signal_line,
        "histogram": macd_values[-1] - signal_line
    }


def ichimoku(
    highs,
    lows,
    tenkan_period=9,
    kijun_period=26,
    senkou_b_period=52
):
    highs = _validate_prices(highs, "highs")
    lows = _validate_prices(lows, "lows")

    if len(highs) != len(lows):
        raise ValueError("High and low arrays must have equal lengths.")

    periods = (
        tenkan_period,
        kijun_period,
        senkou_b_period
    )

    if any(
        not isinstance(p, int) or isinstance(p, bool) or p < 1
        for p in periods
    ):
        raise ValueError("Ichimoku periods must be positive integers.")

    if any(h < l for h, l in zip(highs, lows)):
        raise ValueError("High cannot be lower than low.")

    required = max(periods)

    if len(highs) < required:
        return None

    def midpoint(period):
        recent_highs = highs[-period:]
        recent_lows = lows[-period:]

        return (
            max(recent_highs) + min(recent_lows)
        ) / 2.0

    tenkan = midpoint(tenkan_period)
    kijun = midpoint(kijun_period)
    senkou_a = (tenkan + kijun) / 2.0
    senkou_b = midpoint(senkou_b_period)

    return {
        "tenkan_sen": tenkan,
        "kijun_sen": kijun,
        "senkou_span_a": senkou_a,
        "senkou_span_b": senkou_b,
        "chikou_reference": None,
        "note": (
            "Senkou spans are calculated at the current candle "
            "and must be plotted 26 periods forward. "
            "Chikou requires historical alignment."
        )
    }
