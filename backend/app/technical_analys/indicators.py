
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

    if (
        not isinstance(period, int)
        or isinstance(period, bool)
        or period < 1
    ):
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

    if (
        not isinstance(period, int)
        or isinstance(period, bool)
        or period < 1
    ):
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

    return 100.0 - (
        100.0 / (1.0 + relative_strength)
    )


def atr(highs, lows, closes, period=14):
    highs = _validate_prices(highs, "highs")
    lows = _validate_prices(lows, "lows")
    closes = _validate_prices(closes, "closes")

    if (
        not isinstance(period, int)
        or isinstance(period, bool)
        or period < 1
    ):
        raise ValueError("Period must be a positive integer.")

    if not (len(highs) == len(lows) == len(closes)):
        raise ValueError("OHLC arrays must have equal lengths.")

    for index in range(len(closes)):
        if highs[index] < lows[index]:
            raise ValueError("High cannot be lower than low.")

        if (
            highs[index] < closes[index]
            or lows[index] > closes[index]
        ):
            raise ValueError("Inconsistent OHLC values.")

    if len(closes) < period + 1:
        return None

    true_ranges = []

    for index in range(1, len(closes)):
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
        not isinstance(p, int)
        or isinstance(p, bool)
        or p < 1
        for p in periods
    ):
        raise ValueError(
            "MACD periods must be positive integers."
        )

    if fast >= slow:
        raise ValueError(
            "Fast period must be smaller than slow period."
        )

    if len(prices) < slow + signal - 1:
        return None

    fast_multiplier = 2.0 / (fast + 1)
    slow_multiplier = 2.0 / (slow + 1)

    fast_ema = sum(prices[:fast]) / fast
    slow_ema = sum(prices[:slow]) / slow

    for price in prices[fast:slow]:
        fast_ema = (
            price * fast_multiplier
            + fast_ema * (1 - fast_multiplier)
        )

    macd_values = [fast_ema - slow_ema]

    for price in prices[slow:]:
        fast_ema = (
            price * fast_multiplier
            + fast_ema * (1 - fast_multiplier)
        )

        slow_ema = (
            price * slow_multiplier
            + slow_ema * (1 - slow_multiplier)
        )

        macd_values.append(fast_ema - slow_ema)

    signal_multiplier = 2.0 / (signal + 1)
    signal_line = sum(macd_values[:signal]) / signal

    for value in macd_values[signal:]:
        signal_line = (
            value * signal_multiplier
            + signal_line * (1 - signal_multiplier)
        )

    return {
        "macd": macd_values[-1],
        "signal": signal_line,
        "histogram": macd_values[-1] - signal_line
    }


def ichimoku(
    highs,
    lows,
    closes=None,
    tenkan_period=9,
    kijun_period=26,
    senkou_b_period=52,
    displacement=26
):
    highs = _validate_prices(highs, "highs")
    lows = _validate_prices(lows, "lows")

    if len(highs) != len(lows):
        raise ValueError(
            "High and low arrays must have equal lengths."
        )

    if closes is not None:
        closes = _validate_prices(closes, "closes")

        if len(closes) != len(highs):
            raise ValueError(
                "High, low and close arrays must have equal lengths."
            )

    periods = (
        tenkan_period,
        kijun_period,
        senkou_b_period,
        displacement
    )

    if any(
        not isinstance(p, int)
        or isinstance(p, bool)
        or p < 1
        for p in periods
    ):
        raise ValueError(
            "Ichimoku periods must be positive integers."
        )

    if any(
        high < low
        for high, low in zip(highs, lows)
    ):
        raise ValueError(
            "High cannot be lower than low."
        )

    required = max(
        tenkan_period,
        kijun_period,
        senkou_b_period
    )

    if len(highs) < required:
        return None

    def midpoint(period, end_index):
        start_index = end_index - period + 1

        if start_index < 0:
            return None

        period_highs = highs[start_index:end_index + 1]
        period_lows = lows[start_index:end_index + 1]

        return (
            max(period_highs) + min(period_lows)
        ) / 2.0

    current_index = len(highs) - 1

    tenkan = midpoint(
        tenkan_period,
        current_index
    )

    kijun = midpoint(
        kijun_period,
        current_index
    )

    senkou_a = (tenkan + kijun) / 2.0

    senkou_b = midpoint(
        senkou_b_period,
        current_index
    )

    cloud_index = current_index - displacement

    cloud_at_current = None
    chikou_reference = None
    chikou_position = "UNAVAILABLE"
    price_vs_cloud = "UNAVAILABLE"

    if cloud_index >= 0:
        historical_tenkan = midpoint(
            tenkan_period,
            cloud_index
        )

        historical_kijun = midpoint(
            kijun_period,
            cloud_index
        )

        historical_senkou_b = midpoint(
            senkou_b_period,
            cloud_index
        )

        if (
            historical_tenkan is not None
            and historical_kijun is not None
            and historical_senkou_b is not None
        ):
            historical_senkou_a = (
                historical_tenkan + historical_kijun
            ) / 2.0

            cloud_top = max(
                historical_senkou_a,
                historical_senkou_b
            )

            cloud_bottom = min(
                historical_senkou_a,
                historical_senkou_b
            )

            cloud_at_current = {
                "senkou_span_a": historical_senkou_a,
                "senkou_span_b": historical_senkou_b,
                "top": cloud_top,
                "bottom": cloud_bottom
            }

            if closes is not None:
                current_close = closes[current_index]

                if current_close > cloud_top:
                    price_vs_cloud = "ABOVE"
                elif current_close < cloud_bottom:
                    price_vs_cloud = "BELOW"
                else:
                    price_vs_cloud = "INSIDE"

    if closes is not None and cloud_index >= 0:
        chikou_reference = closes[cloud_index]
        current_close = closes[current_index]

        if current_close > chikou_reference:
            chikou_position = "ABOVE"
        elif current_close < chikou_reference:
            chikou_position = "BELOW"
        else:
            chikou_position = "EQUAL"

    if senkou_a > senkou_b:
        projected_cloud_bias = "BULLISH"
    elif senkou_a < senkou_b:
        projected_cloud_bias = "BEARISH"
    else:
        projected_cloud_bias = "NEUTRAL"

    if tenkan > kijun:
        tenkan_kijun_bias = "BULLISH"
    elif tenkan < kijun:
        tenkan_kijun_bias = "BEARISH"
    else:
        tenkan_kijun_bias = "NEUTRAL"

    return {
        "tenkan_sen": tenkan,
        "kijun_sen": kijun,
        "senkou_span_a": senkou_a,
        "senkou_span_b": senkou_b,
        "projected_cloud_bias": projected_cloud_bias,
        "tenkan_kijun_bias": tenkan_kijun_bias,
        "cloud_at_current": cloud_at_current,
        "price_vs_cloud": price_vs_cloud,
        "chikou_value": (
            closes[-1] if closes is not None else None
        ),
        "chikou_reference": chikou_reference,
        "chikou_position": chikou_position,
        "displacement": displacement,
        "note": (
            "Current cloud uses Senkou values calculated "
            "displacement candles earlier. Projected spans "
            "are calculated from the latest candle. "
            "No future candle data is used."
        )
    }
