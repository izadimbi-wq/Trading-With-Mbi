from math import isfinite
from .indicators import ema, rsi, atr, macd, ichimoku
from .signal_engine import generate_signal
from .levels import support_resistance, pullback_zone

SUPPORTED_TIMEFRAMES = {"M1", "M5", "M15", "M30", "H1", "H4", "D1"}
SETTINGS = {
    "ema_fast": 20, "ema_slow": 50, "rsi": 14, "atr": 14,
    "macd_fast": 12, "macd_slow": 26, "macd_signal": 9,
    "tenkan": 9, "kijun": 26, "senkou_b": 52, "displacement": 26,
}
CURRENCY_CODES = {
    "USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD",
    "CNH", "CNY", "HKD", "SGD", "SEK", "NOK", "DKK", "PLN",
    "CZK", "HUF", "TRY", "ZAR", "MXN", "ILS", "THB", "AED",
}
METALS = {"XAU", "XAG", "XPT", "XPD"}


def normalize_symbol(symbol):
    raw = "".join(ch for ch in str(symbol).upper() if ch.isalpha())
    allowed = CURRENCY_CODES | METALS
    for i in range(max(1, len(raw) - 5)):
        candidate = raw[i:i + 6]
        if len(candidate) == 6 and candidate[:3] in allowed and candidate[3:] in allowed:
            return candidate
    return raw


def supported_symbol(symbol):
    s = normalize_symbol(symbol)
    if len(s) != 6:
        return False
    base, quote = s[:3], s[3:]
    return ((base in CURRENCY_CODES and quote in CURRENCY_CODES and base != quote)
            or (base in METALS and quote in {"USD", "EUR", "GBP", "JPY", "CHF"}))


def validate_market_input(symbol, timeframe, candles):
    symbol, timeframe = normalize_symbol(symbol), str(timeframe).upper()
    if not supported_symbol(symbol):
        raise ValueError("Unsupported trading symbol.")
    if timeframe not in SUPPORTED_TIMEFRAMES:
        raise ValueError("Unsupported timeframe.")
    if not isinstance(candles, list) or not candles:
        raise ValueError("Candles must be a non-empty list.")
    required = ("open", "high", "low", "close")
    for idx, candle in enumerate(candles):
        if not isinstance(candle, dict) or not all(k in candle for k in required):
            raise ValueError(f"Incomplete candle {idx}.")
        if candle.get("isOpen") is True or candle.get("is_open") is True:
            raise ValueError("Open candles must be excluded.")
        values = [candle[k] for k in required]
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not isfinite(v) or v <= 0 for v in values):
            raise ValueError(f"Invalid candle {idx}.")
        if candle["high"] < max(candle["open"], candle["close"]) or candle["low"] > min(candle["open"], candle["close"]) or candle["high"] < candle["low"]:
            raise ValueError(f"Invalid OHLC candle {idx}.")
    return {"symbol": symbol, "timeframe": timeframe, "candles": candles}


def calculate_indicators(candles):
    s = SETTINGS
    closes = [x["close"] for x in candles]
    highs, lows = [x["high"] for x in candles], [x["low"] for x in candles]
    required = max(s["ema_slow"], s["rsi"] + 1, s["atr"] + 1,
                   s["macd_slow"] + s["macd_signal"] - 1, s["senkou_b"] + s["displacement"])
    if len(candles) < required:
        return {"status": "INSUFFICIENT_DATA", "required_candles": required, "available_candles": len(candles)}
    values = {
        "ema": {"fast": ema(closes, s["ema_fast"]), "slow": ema(closes, s["ema_slow"]),
                "fast_period": s["ema_fast"], "slow_period": s["ema_slow"]},
        "rsi": {"period": s["rsi"], "value": rsi(closes, s["rsi"])},
        "atr": {"period": s["atr"], "value": atr(highs, lows, closes, s["atr"])},
        "macd": macd(closes, s["macd_fast"], s["macd_slow"], s["macd_signal"]),
        "ichimoku": ichimoku(highs, lows, closes, s["tenkan"], s["kijun"], s["senkou_b"], s["displacement"]),
    }
    return {"status": "CALCULATED", "candles_used": len(candles),
            "price_scale": {"last_close": closes[-1], "minimum_close": min(closes), "maximum_close": max(closes)},
            "indicators": values}


def analyze_market(symbol, timeframe, candles, account=None, contract=None, quote=None):
    validated = validate_market_input(symbol, timeframe, candles)
    data = validated["candles"]
    result = calculate_indicators(data)
    result.update({"symbol": validated["symbol"], "timeframe": validated["timeframe"]})
    if result["status"] != "CALCULATED":
        result.update({"signal": "NO TRADE", "technical_signal": "NO TRADE",
                       "signal_status": "INSUFFICIENT_DATA", "signal_reason": "Not enough closed candles.",
                       "trade_status": "NOT_EVALUATED",
                       "trade_plan": {"status": "UNAVAILABLE", "reason": "Insufficient candle history."}})
        return result

    indicators = result["indicators"]
    signal = generate_signal(indicators)
    direction = signal["signal"]
    result.update({
        "signal": direction, "technical_signal": direction,
        "signal_status": signal["status"], "signal_reason": signal["reason"],
        "signal_details": signal,
        "trend": "BULLISH" if indicators["ema"]["fast"] > indicators["ema"]["slow"] else
                 "BEARISH" if indicators["ema"]["fast"] < indicators["ema"]["slow"] else "NEUTRAL",
        "support_resistance": support_resistance(data, indicators["atr"]["value"]),
        "pullback": pullback_zone(data, indicators["atr"]["value"]),
        "technical_reference_price": data[-1]["close"],
        "note": "Closed-candle analysis only. No order is sent. S/R and pullback are estimates.",
    })

    if quote is None or quote.get("stale") is not False:
        result.update({"signal": "NO TRADE", "signal_status": "QUOTE_UNAVAILABLE",
                       "signal_reason": "A verified fresh Bid/Ask quote is required.",
                       "trade_status": "BLOCKED_QUOTE_UNAVAILABLE",
                       "trade_plan": {"status": "UNAVAILABLE", "reason": "Fresh Bid/Ask quote unavailable."}})
        return result
    bid, ask = quote.get("bid"), quote.get("ask")
    if (isinstance(bid, bool) or isinstance(ask, bool) or
        not isinstance(bid, (int, float)) or not isinstance(ask, (int, float)) or
        not isfinite(bid) or not isfinite(ask) or bid <= 0 or ask < bid):
        result.update({"signal": "NO TRADE", "signal_status": "INVALID_QUOTE",
                       "signal_reason": "Bid/Ask quote is invalid.", "trade_status": "BLOCKED_INVALID_QUOTE",
                       "trade_plan": {"status": "UNAVAILABLE", "reason": "Invalid Bid/Ask quote."}})
        return result

    result.update({"bid": bid, "ask": ask, "spread": ask - bid})
    result["entry_price"] = ask if direction == "BUY" else bid if direction == "SELL" else None
    result["entry_price_type"] = "ASK" if direction == "BUY" else "BID" if direction == "SELL" else None
    result["trade_plan"] = {"status": "NOT_REQUESTED"}
    if direction not in ("BUY", "SELL"):
        result["trade_status"], result["trade_status_reason"] = "NO_SETUP", signal["reason"]
        return result
    if account is None:
        result.update({"signal": "NO TRADE", "signal_status": "BLOCKED_RISK_PROFILE_MISSING",
                       "signal_reason": "Account balance and risk settings are required.",
                       "trade_status": "BLOCKED_RISK_PROFILE_MISSING",
                       "trade_plan": {"status": "UNAVAILABLE", "reason": "Account risk profile missing."}})
        return result
    if contract is None:
        result.update({"signal": "NO TRADE", "signal_status": "BLOCKED_CONTRACT_UNVERIFIED",
                       "signal_reason": "Technical direction detected, but broker contract specifications are not verified.",
                       "trade_status": "BLOCKED_CONTRACT_UNVERIFIED",
                       "trade_plan": {"status": "UNAVAILABLE",
                                      "reason": "Verify tick size, tick value per lot, minimum lot, lot step and maximum lot in the live MT4 Specification."}})
        return result

    from risk_management.trade_plan import TradePlanRequest, create_trade_plan
    plan = create_trade_plan(TradePlanRequest(
        balance=account["balance"], risk_percent=account.get("risk_percent", 1),
        entry_price=result["entry_price"], atr_value=indicators["atr"]["value"],
        direction=direction, tick_size=contract["tick_size"],
        tick_value_per_lot=contract["tick_value_per_lot"], min_lot=contract["min_lot"],
        lot_step=contract["lot_step"], max_lot=contract["max_lot"]))
    result["trade_plan"] = plan
    if plan["status"] == "ACCEPT_FOR_REVIEW":
        result["trade_status"] = "ACCEPT_FOR_REVIEW"
        result["trade_status_reason"] = "Risk controls passed; manual review is required."
    else:
        result.update({"signal": "NO TRADE", "signal_status": "RISK_REJECTED",
                       "signal_reason": "Risk controls rejected the proposed trade: " + plan.get("reason", ""),
                       "trade_status": "REJECTED_RISK_CONTROLS"})
    return result
