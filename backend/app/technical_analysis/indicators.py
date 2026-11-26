from math import isfinite


def _numeric_series(values, name="values", positive_only=False):
    """Validate a non-empty numeric series.

    Price series must be strictly positive. Derived indicator series such as
    MACD may legitimately contain zero and negative values.
    """
    if not isinstance(values, (list, tuple)) or not values:
        raise ValueError(f"{name} must be a non-empty list or tuple.")

    out = []
    for value in values:
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not isfinite(value)
            or (positive_only and value <= 0)
        ):
            raise ValueError(f"Invalid value in {name}.")
        out.append(float(value))
    return out


def _prices(values, name="prices"):
    """Validate market prices, which must be finite and strictly positive."""
    return _numeric_series(values, name=name, positive_only=True)


def _ema_numeric(values, period):
    """EMA for a finite numeric series, including signed derived values."""
    if isinstance(period, bool) or not isinstance(period, int) or period < 1:
        raise ValueError("Period must be positive.")

    if len(values) < period:
        return None

    multiplier = 2.0 / (period + 1.0)
    value = sum(values[:period]) / period

    for item in values[period:]:
        value = item * multiplier + value * (1.0 - multiplier)

    return value


def ema(prices, period):
    """EMA of actual market prices."""
    values = _prices(prices)
    return _ema_numeric(values, period)


def rsi(prices, period=14):
    values = _prices(prices)

    if isinstance(period, bool) or not isinstance(period, int) or period < 1:
        raise ValueError("Period must be positive.")

    if len(values) < period + 1:
        return None

    changes = [
        values[index] - values[index - 1]
        for index in range(1, len(values))
    ]
    gains = [max(change, 0.0) for change in changes]
    losses = [max(-change, 0.0) for change in changes]

    average_gain = sum(gains[:period]) / period
    average_loss = sum(losses[:period]) / period

    for index in range(period, len(changes)):
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
    return 100.0 - 100.0 / (1.0 + relative_strength)


def atr(highs, lows, closes, period=14):
    high_values = _prices(highs, "highs")
    low_values = _prices(lows, "lows")
    close_values = _prices(closes, "closes")

    if not (
        len(high_values) == len(low_values) == len(close_values)
    ):
        raise ValueError("OHLC arrays must have equal lengths.")

    if isinstance(period, bool) or not isinstance(period, int) or period < 1:
        raise ValueError("Period must be positive.")

    if any(
        high < low or high < close or low > close
        for high, low, close in zip(
            high_values, low_values, close_values
        )
    ):
        raise ValueError("Inconsistent OHLC.")

    if len(close_values) < period + 1:
        return None

    true_ranges = [
        max(
            high_values[index] - low_values[index],
            abs(high_values[index] - close_values[index - 1]),
            abs(low_values[index] - close_values[index - 1]),
        )
        for index in range(1, len(close_values))
    ]

    value = sum(true_ranges[:period]) / period

    for item in true_ranges[period:]:
        value = (value * (period - 1) + item) / period

    return value


def macd(prices, fast=12, slow=26, signal=9):
    price_values = _prices(prices)

    if any(
        isinstance(period, bool)
        or not isinstance(period, int)
        or period < 1
        for period in (fast, slow, signal)
    ) or fast >= slow:
        raise ValueError("Invalid MACD periods.")

    if len(price_values) < slow + signal - 1:
        return None

    def ema_series(values, period):
        multiplier = 2.0 / (period + 1.0)
        current = sum(values[:period]) / period
        output = [None] * (period - 1) + [current]

        for item in values[period:]:
            current = item * multiplier + current * (1.0 - multiplier)
            output.append(current)

        return output

    fast_series = ema_series(price_values, fast)
    slow_series = ema_series(price_values, slow)

    macd_line = [
        fast_series[index] - slow_series[index]
        for index in range(slow - 1, len(price_values))
    ]

    # MACD values are differences, so they can be negative or zero.
    # Do not pass this derived series through the positive-price validator.
    signal_line = _ema_numeric(macd_line, signal)

    if signal_line is None:
        return None

    latest_macd = macd_line[-1]

    return {
        "macd": latest_macd,
        "signal": signal_line,
        "histogram": latest_macd - signal_line,
    }


def ichimoku(
    highs,
    lows,
    closes=None,
    tenkan_period=9,
    kijun_period=26,
    senkou_b_period=52,
    displacement=26,
):
    high_values = _prices(highs, "highs")
    low_values = _prices(lows, "lows")
    close_values = _prices(closes, "closes") if closes is not None else None

    if len(high_values) != len(low_values) or (
        close_values is not None
        and len(close_values) != len(high_values)
    ):
        raise ValueError("OHLC arrays must have equal lengths.")

    periods = (
        tenkan_period,
        kijun_period,
        senkou_b_period,
        displacement,
    )

    if any(
        isinstance(period, bool)
        or not isinstance(period, int)
        or period < 1
        for period in periods
    ):
        raise ValueError("Invalid Ichimoku periods.")

    if any(
        high < low
        for high, low in zip(high_values, low_values)
    ):
        raise ValueError("High cannot be below low.")

    if len(high_values) < max(
        tenkan_period, kijun_period, senkou_b_period
    ):
        return None

    def midpoint(period, end_index):
        start_index = end_index - period + 1
        if start_index < 0:
            return None

        window_highs = high_values[start_index:end_index + 1]
        window_lows = low_values[start_index:end_index + 1]

        return (max(window_highs) + min(window_lows)) / 2.0

    index = len(high_values) - 1

    tenkan = midpoint(tenkan_period, index)
    kijun = midpoint(kijun_period, index)
    span_a = (tenkan + kijun) / 2.0
    span_b = midpoint(senkou_b_period, index)

    cloud_index = index - displacement
    cloud = None
    price_position = "UNAVAILABLE"
    chikou_reference = None
    chikou_position = "UNAVAILABLE"

    if cloud_index >= 0:
        historical_tenkan = midpoint(tenkan_period, cloud_index)
        historical_kijun = midpoint(kijun_period, cloud_index)
        historical_span_b = midpoint(senkou_b_period, cloud_index)

        if None not in (
            historical_tenkan,
            historical_kijun,
            historical_span_b,
        ):
            historical_span_a = (
                historical_tenkan + historical_kijun
            ) / 2.0
            cloud_top = max(historical_span_a, historical_span_b)
            cloud_bottom = min(historical_span_a, historical_span_b)

            cloud = {
                "senkou_span_a": historical_span_a,
                "senkou_span_b": historical_span_b,
                "top": cloud_top,
                "bottom": cloud_bottom,
            }

            if close_values is not None:
                latest_close = close_values[-1]
                price_position = (
                    "ABOVE" if latest_close > cloud_top
                    else "BELOW" if latest_close < cloud_bottom
                    else "INSIDE"
                )

        if close_values is not None:
            chikou_reference = close_values[cloud_index]
            latest_close = close_values[-1]
            chikou_position = (
                "ABOVE" if latest_close > chikou_reference
                else "BELOW" if latest_close < chikou_reference
                else "EQUAL"
            )

    return {
        "tenkan_sen": tenkan,
        "kijun_sen": kijun,
        "senkou_span_a": span_a,
        "senkou_span_b": span_b,
        "projected_cloud_bias": (
            "BULLISH" if span_a > span_b
            else "BEARISH" if span_a < span_b
            else "NEUTRAL"
        ),
        "tenkan_kijun_bias": (
            "BULLISH" if tenkan > kijun
            else "BEARISH" if tenkan < kijun
            else "NEUTRAL"
        ),
        "cloud_at_current": cloud,
        "price_vs_cloud": price_position,
        "chikou_value": close_values[-1] if close_values else None,
        "chikou_reference": chikou_reference,
        "chikou_position": chikou_position,
        "displacement": displacement,
        "note": "Chikou is informational only; no future candles are used.",
    }
