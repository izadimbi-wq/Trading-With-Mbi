
import pytest

from technical_analysis.strategy import (
    validate_market_input,
    analyze_market
)


def sample_candles():
    return [
        {
            "open": 2000.0,
            "high": 2010.0,
            "low": 1990.0,
            "close": 2005.0
        },
        {
            "open": 2005.0,
            "high": 2020.0,
            "low": 2000.0,
            "close": 2015.0
        }
    ]


def long_sample_candles(count=90):
    candles = []

    for i in range(count):
        close = 2000.0 + i

        candles.append({
            "open": close - 0.5,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close
        })

    return candles


def test_valid_market_input():
    result = validate_market_input(
        "XAUUSD",
        "M5",
        sample_candles()
    )

    assert result["symbol"] == "XAUUSD"
    assert result["timeframe"] == "M5"
    assert len(result["candles"]) == 2


def test_unsupported_symbol():
    with pytest.raises(ValueError):
        validate_market_input(
            "BTCUSD",
            "M5",
            sample_candles()
        )


def test_unsupported_timeframe():
    with pytest.raises(ValueError):
        validate_market_input(
            "XAUUSD",
            "M2",
            sample_candles()
        )


def test_empty_candles():
    with pytest.raises(ValueError):
        validate_market_input(
            "XAUUSD",
            "M5",
            []
        )


def test_invalid_ohlc():
    candles = [
        {
            "open": 2000.0,
            "high": 1990.0,
            "low": 1980.0,
            "close": 2005.0
        }
    ]

    with pytest.raises(ValueError):
        validate_market_input(
            "XAUUSD",
            "M5",
            candles
        )


def test_full_market_analysis():
    result = analyze_market(
        "XAUUSD",
        "M5",
        long_sample_candles()
    )

    assert result["status"] == "CALCULATED"
    assert result["symbol"] == "XAUUSD"
    assert result["timeframe"] == "M5"

    indicators = result["indicators"]

    assert indicators["ema"]["fast"] is not None
    assert indicators["ema"]["slow"] is not None
    assert indicators["rsi"]["value"] is not None
    assert indicators["atr"]["value"] > 0
    assert indicators["macd"] is not None

    ichimoku_result = indicators["ichimoku"]

    assert ichimoku_result is not None
    assert ichimoku_result["cloud_at_current"] is not None

    assert ichimoku_result["price_vs_cloud"] in (
        "ABOVE",
        "BELOW",
        "INSIDE"
    )

    assert ichimoku_result["chikou_reference"] is not None

    assert ichimoku_result["chikou_position"] in (
        "ABOVE",
        "BELOW",
        "EQUAL"
    )

    assert result["signal"] in (
        "BUY",
        "SELL",
        "NO TRADE"
    )

    assert result["signal_status"] in (
        "SIGNAL_GENERATED",
        "NO_VALID_SETUP",
        "INVALID_INDICATOR_DATA",
        "INSUFFICIENT_DATA"
    )

    assert isinstance(result["signal_details"], dict)
    assert result["signal_details"]["signal"] == result["signal"]


def test_insufficient_market_data():
    result = analyze_market(
        "EURUSD",
        "M5",
        long_sample_candles(77)
    )

    assert result["status"] == "INSUFFICIENT_DATA"
    assert result["required_candles"] == 78
    assert result["available_candles"] == 77

    assert result["signal"] == "NO TRADE"
    assert result["signal_status"] == "INSUFFICIENT_DATA"


def test_open_candle_is_rejected():
    candles = long_sample_candles()
    candles[-1]["isOpen"] = True

    with pytest.raises(ValueError):
        analyze_market(
            "XAUUSD",
            "M5",
            candles
        )
