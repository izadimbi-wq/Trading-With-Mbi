from math import isfinite

from .indicators import ema, rsi, atr, macd, ichimoku
from .signal_engine import generate_signal
from .levels import support_resistance, pullback_zone

SUPPORTED_SYMBOLS = {"XAUUSD", "EURUSD", "XAGUSD"}
SUPPORTED_TIMEFRAMES = {"M1", "M5", "M15", "M30", "H1", "H4", "D1"}

SETTINGS = {
    "ema_fast": 20,
    "ema_slow": 50,
    "rsi": 14,
    "atr": 14,
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,
    "tenkan": 9,
    "kijun": 26,
    "senkou_b": 52,
    "displacement": 26,
}

# Broad sanity bands catch candles belonging to a different instrument.
# These are validation guards, not trading targets or price forecasts.
SYMBOL_PRICE_BANDS = {
    "XAUUSD": (100.0, 100000.0),
    "EURUSD": (0.1, 10.0),
    "XAGUSD": (1.0, 1000.0),
}


def validate_market_input(symbol, timeframe, candles):
    symbol = str(symbol).upper()
    timeframe = str(timeframe).upper()

    if symbol not in SUPPORTED_SYMBOLS:
        raise ValueError("Unsupported trading symbol.")
    if timeframe not in SUPPORTED_TIMEFRAMES:
        raise ValueError("Unsupported timeframe.")
    if not isinstance(candles, list) or not candles:
        raise ValueError("Candles must be a non-empty list.")

    low_band, high_band = SYMBOL_PRICE_BANDS[symbol]
    required = ("open", "high", "low", "close")

    for idx, candle in enumerate(candles):
        if not isinstance(candle, dict) or not all(
            key in candle for key in required
        ):
            raise ValueError(f"Incomplete candle {idx}.")

        if candle.get("isOpen") is True or candle.get("is_open") is True:
            raise ValueError("Open candles must be excluded.")

        values = [candle[key] for key in required]
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not isfinite(value)
            or value <= 0
            for value in values
        ):
            raise ValueError(f"Invalid candle {idx}.")

        if any(value < low_band or value > high_band for value in values):
            raise ValueError(
                f"PRICE_SCALE_MISMATCH: candle prices do not match {symbol}; "
                f"expected {low_band:g}..{high_band:g}."
            )

        if (
            candle["high"] < max(candle["open"], candle["close"])
            or candle["low"] > min(candle["open"], candle["close"])
            or candle["high"] < candle["low"]
        ):
            raise ValueError(f"Invalid OHLC candle {idx}.")

    return {"symbol": symbol, "timeframe": timeframe, "candles": candles}


def calculate_indicators(candles):
    settings = SETTINGS
    closes = [item["close"] for item in candles]
    highs = [item["high"] for item in candles]
    lows = [item["low"] for item in candles]

    required = max(
        settings["ema_slow"],
        settings["rsi"] + 1,
        settings["atr"] + 1,
        settings["macd_slow"] + settings["macd_signal"] - 1,
        settings["senkou_b"] + settings["displacement"],
    )

    if len(candles) < required:
        return {
            "status": "INSUFFICIENT_DATA",
            "required_candles": required,
            "available_candles": len(candles),
        }

    values = {
        "ema": {
            "fast": ema(closes, settings["ema_fast"]),
            "slow": ema(closes, settings["ema_slow"]),
            "fast_period": settings["ema_fast"],
            "slow_period": settings["ema_slow"],
        },
        "rsi": {
            "period": settings["rsi"],
            "value": rsi(closes, settings["rsi"]),
        },
        "atr": {
            "period": settings["atr"],
            "value": atr(highs, lows, closes, settings["atr"]),
        },
        "macd": macd(
            closes,
            settings["macd_fast"],
            settings["macd_slow"],
            settings["macd_signal"],
        ),
        "ichimoku": ichimoku(
            highs,
            lows,
            closes,
            settings["tenkan"],
            settings["kijun"],
            settings["senkou_b"],
            settings["displacement"],
        ),
    }

    return {
        "status": "CALCULATED",
        "candles_used": len(candles),
        "price_scale": {
            "last_close": closes[-1],
            "minimum_close": min(closes),
            "maximum_close": max(closes),
        },
        "indicators": values,
    }


def analyze_market(symbol, timeframe, candles, account=None, contract=None):
    validated = validate_market_input(symbol, timeframe, candles)
    data = validated["candles"]
    result = calculate_indicators(data)
    result.update({
        "symbol": validated["symbol"],
        "timeframe": validated["timeframe"],
    })

    if result["status"] != "CALCULATED":
        result.update({
            "signal": "NO TRADE",
            "signal_status": "INSUFFICIENT_DATA",
            "signal_reason": "Not enough closed candles.",
            "trade_plan": {
                "status": "UNAVAILABLE",
                "reason": "Insufficient candle history.",
            },
        })
        return result

    indicators = result["indicators"]
    signal = generate_signal(indicators)

    result.update({
        "signal": signal["signal"],
        "signal_status": signal["status"],
        "signal_reason": signal["reason"],
        "signal_details": signal,
        "trend": (
            "BULLISH" if indicators["ema"]["fast"] > indicators["ema"]["slow"]
            else "BEARISH" if indicators["ema"]["fast"] < indicators["ema"]["slow"]
            else "NEUTRAL"
        ),
        "support_resistance": support_resistance(
            data, indicators["atr"]["value"]
        ),
        "pullback": pullback_zone(data, indicators["atr"]["value"]),
        "entry_price": data[-1]["close"],
        "note": (
            "Closed-candle analysis only. No order is sent. "
            "S/R and pullback are estimates."
        ),
    })

    result["trade_plan"] = {"status": "NOT_REQUESTED"}

    if signal["signal"] in ("BUY", "SELL"):
        if account is None:
            result["signal"] = "NO TRADE"
            result["signal_status"] = "RISK_PROFILE_MISSING"
            result["signal_reason"] = (
                "Account balance and risk settings are required."
            )
            result["trade_plan"] = {
                "status": "UNAVAILABLE",
                "reason": "Account risk profile missing.",
            }

        elif contract is None:
            result["signal"] = "NO TRADE"
            result["signal_status"] = "CONTRACT_UNVERIFIED"
            result["signal_reason"] = (
                "Technical setup detected, but trading is blocked until "
                "live broker contract specifications are verified."
            )
            result["trade_plan"] = {
                "status": "UNAVAILABLE",
                "reason": (
                    "Verify tick size, tick value per lot, minimum lot, "
                    "lot step and maximum lot in MT4."
                ),
            }

        else:
            from risk_management.trade_plan import (
                TradePlanRequest,
                create_trade_plan,
            )

            plan = create_trade_plan(TradePlanRequest(
                balance=account["balance"],
                risk_percent=account.get("risk_percent", 1),
                entry_price=data[-1]["close"],
                atr_value=indicators["atr"]["value"],
                direction=signal["signal"],
                tick_size=contract["tick_size"],
                tick_value_per_lot=contract["tick_value_per_lot"],
                min_lot=contract["min_lot"],
                lot_step=contract["lot_step"],
                max_lot=contract["max_lot"],
            ))

            result["trade_plan"] = plan
            if plan["status"] != "ACCEPT_FOR_REVIEW":
                result["signal"] = "NO TRADE"
                result["signal_status"] = "RISK_REJECTED"
                result["signal_reason"] = (
                    "Signal rejected by risk controls: "
                    + plan.get("reason", "")
                )

    return result
