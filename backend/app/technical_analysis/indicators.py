from math import isfinite


def _prices(values, name="prices"):
    if not isinstance(values, (list, tuple)) or not values:
        raise ValueError(f"{name} must be a non-empty list or tuple.")
    out = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or value <= 0:
            raise ValueError(f"Invalid value in {name}.")
        out.append(float(value))
    return out


def _finite_series(values, name="values"):
    """Validate finite derived values; zero and negatives are valid here."""
    if not isinstance(values, (list, tuple)) or not values:
        raise ValueError(f"{name} must be a non-empty list or tuple.")
    out = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
            raise ValueError(f"Invalid value in {name}.")
        out.append(float(value))
    return out


def _ema_series(values, period, name="values"):
    data = _finite_series(values, name)
    if isinstance(period, bool) or not isinstance(period, int) or period < 1:
        raise ValueError("Period must be positive.")
    if len(data) < period:
        return None
    k = 2 / (period + 1)
    value = sum(data[:period]) / period
    for item in data[period:]:
        value = item * k + value * (1 - k)
    return value


def ema(prices, period):
    # EMA of actual market prices: keep strict positive-price validation.
    data = _prices(prices)
    return _ema_series(data, period, "prices")


def rsi(prices, period=14):
    p = _prices(prices)
    if isinstance(period, bool) or not isinstance(period, int) or period < 1:
        raise ValueError("Period must be positive.")
    if len(p) < period + 1:
        return None
    changes = [p[i] - p[i - 1] for i in range(1, len(p))]
    gains = [max(x, 0) for x in changes]
    losses = [max(-x, 0) for x in changes]
    ag = sum(gains[:period]) / period
    al = sum(losses[:period]) / period
    for i in range(period, len(changes)):
        ag = (ag * (period - 1) + gains[i]) / period
        al = (al * (period - 1) + losses[i]) / period
    if al == 0:
        return 100.0 if ag > 0 else 50.0
    if ag == 0:
        return 0.0
    return 100 - 100 / (1 + ag / al)


def atr(highs, lows, closes, period=14):
    h = _prices(highs, "highs")
    l = _prices(lows, "lows")
    c = _prices(closes, "closes")
    if not (len(h) == len(l) == len(c)):
        raise ValueError("OHLC arrays must have equal lengths.")
    if isinstance(period, bool) or not isinstance(period, int) or period < 1:
        raise ValueError("Period must be positive.")
    if any(hi < lo or hi < cl or lo > cl for hi, lo, cl in zip(h, l, c)):
        raise ValueError("Inconsistent OHLC.")
    if len(c) < period + 1:
        return None
    tr = [max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
          for i in range(1, len(c))]
    value = sum(tr[:period]) / period
    for item in tr[period:]:
        value = (value * (period - 1) + item) / period
    return value


def macd(prices, fast=12, slow=26, signal=9):
    p = _prices(prices)
    if any(isinstance(x, bool) or not isinstance(x, int) or x < 1
           for x in (fast, slow, signal)) or fast >= slow:
        raise ValueError("Invalid MACD periods.")
    if len(p) < slow + signal - 1:
        return None

    def ema_values(values, period):
        k = 2 / (period + 1)
        value = sum(values[:period]) / period
        out = [None] * (period - 1) + [value]
        for item in values[period:]:
            value = item * k + value * (1 - k)
            out.append(value)
        return out

    fast_values = ema_values(p, fast)
    slow_values = ema_values(p, slow)
    line = [fast_values[i] - slow_values[i] for i in range(slow - 1, len(p))]
    # MACD is a difference series and can legitimately be negative or zero.
    signal_value = _ema_series(line, signal, "MACD values")
    latest = line[-1]
    return {"macd": latest, "signal": signal_value,
            "histogram": latest - signal_value}


def ichimoku(highs, lows, closes=None, tenkan_period=9, kijun_period=26,
             senkou_b_period=52, displacement=26):
    h = _prices(highs, "highs")
    l = _prices(lows, "lows")
    c = _prices(closes, "closes") if closes is not None else None
    if len(h) != len(l) or (c is not None and len(c) != len(h)):
        raise ValueError("OHLC arrays must have equal lengths.")
    if any(x < 1 for x in (tenkan_period, kijun_period, senkou_b_period, displacement)):
        raise ValueError("Invalid Ichimoku periods.")
    if any(hi < lo for hi, lo in zip(h, l)):
        raise ValueError("High cannot be below low.")
    if len(h) < max(tenkan_period, kijun_period, senkou_b_period):
        return None

    def mid(period, end):
        start = end - period + 1
        if start < 0:
            return None
        return (max(h[start:end + 1]) + min(l[start:end + 1])) / 2

    i = len(h) - 1
    ten = mid(tenkan_period, i)
    kij = mid(kijun_period, i)
    sa = (ten + kij) / 2
    sb = mid(senkou_b_period, i)
    ci = i - displacement
    cloud = None
    pos = "UNAVAILABLE"
    chikou_ref = None
    chikou_pos = "UNAVAILABLE"
    if ci >= 0:
        ht, hk, hb = mid(tenkan_period, ci), mid(kijun_period, ci), mid(senkou_b_period, ci)
        if None not in (ht, hk, hb):
            ha = (ht + hk) / 2
            top, bottom = max(ha, hb), min(ha, hb)
            cloud = {"senkou_span_a": ha, "senkou_span_b": hb, "top": top, "bottom": bottom}
            if c:
                pos = "ABOVE" if c[-1] > top else "BELOW" if c[-1] < bottom else "INSIDE"
        if c:
            chikou_ref = c[ci]
            chikou_pos = "ABOVE" if c[-1] > chikou_ref else "BELOW" if c[-1] < chikou_ref else "EQUAL"
    return {
        "tenkan_sen": ten, "kijun_sen": kij, "senkou_span_a": sa, "senkou_span_b": sb,
        "projected_cloud_bias": "BULLISH" if sa > sb else "BEARISH" if sa < sb else "NEUTRAL",
        "tenkan_kijun_bias": "BULLISH" if ten > kij else "BEARISH" if ten < kij else "NEUTRAL",
        "cloud_at_current": cloud, "price_vs_cloud": pos,
        "chikou_value": c[-1] if c else None, "chikou_reference": chikou_ref,
        "chikou_position": chikou_pos, "displacement": displacement,
        "note": "Chikou is informational only; no future candles are used.",
    }
