
import pytest

from technical_analysis.signal_engine import generate_signal


def bullish_indicators():
    return {
        "ema": {
            "fast": 2050.0,
            "slow": 2040.0
        },
        "rsi": {
            "value": 60.0
        },
        "atr": {
            "value": 12.0
        },
        "macd": {
            "macd": 2.5,
            "signal": 1.5,
            "histogram": 1.0
        },
        "ichimoku": {
            "price_vs_cloud": "ABOVE",
            "tenkan_kijun_bias": "BULLISH"
        }
    }


def bearish_indicators():
    return {
        "ema": {
            "fast": 2030.0,
            "slow": 2040.0
        },
        "rsi": {
            "value": 40.0
        },
        "atr": {
            "value": 10.0
        },
        "macd": {
            "macd": -2.5,
            "signal": -1.5,
            "histogram": -1.0
        },
        "ichimoku": {
            "price_vs_cloud": "BELOW",
            "tenkan_kijun_bias": "BEARISH"
        }
    }


def test_buy_signal():
    result = generate_signal(bullish_indicators())

    assert result["signal"] == "BUY"
    assert result["status"] == "SIGNAL_GENERATED"
    assert len(result["buy_confirmations"]) == 5
    assert len(result["sell_confirmations"]) == 0


def test_sell_signal():
    result = generate_signal(bearish_indicators())

    assert result["signal"] == "SELL"
    assert result["status"] == "SIGNAL_GENERATED"
    assert len(result["sell_confirmations"]) == 5
    assert len(result["buy_confirmations"]) == 0


def test_no_trade_when_conditions_conflict():
    indicators = bullish_indicators()

    indicators["ichimoku"]["price_vs_cloud"] = "BELOW"

    result = generate_signal(indicators)

    assert result["signal"] == "NO TRADE"
    assert result["status"] == "NO_VALID_SETUP"


def test_no_trade_when_rsi_is_overbought():
    indicators = bullish_indicators()
    indicators["rsi"]["value"] = 75.0

    result = generate_signal(indicators)

    assert result["signal"] == "NO TRADE"


def test_no_trade_when_price_is_inside_cloud():
    indicators = bullish_indicators()
    indicators["ichimoku"]["price_vs_cloud"] = "INSIDE"

    result = generate_signal(indicators)

    assert result["signal"] == "NO TRADE"


def test_no_trade_when_atr_is_invalid():
    indicators = bullish_indicators()
    indicators["atr"]["value"] = 0

    result = generate_signal(indicators)

    assert result["signal"] == "NO TRADE"
    assert result["status"] == "INVALID_INDICATOR_DATA"


def test_no_trade_when_indicator_value_is_missing():
    indicators = bullish_indicators()
    indicators["ema"]["fast"] = None

    result = generate_signal(indicators)

    assert result["signal"] == "NO TRADE"
    assert result["status"] == "INVALID_INDICATOR_DATA"


def test_missing_indicator_group_raises_error():
    indicators = bullish_indicators()
    del indicators["macd"]

    with pytest.raises(ValueError):
        generate_signal(indicators)


def test_invalid_indicator_structure_raises_error():
    indicators = bullish_indicators()
    indicators["atr"] = 10.0

    with pytest.raises(ValueError):
        generate_signal(indicators)


def test_signal_does_not_execute_orders():
    result = generate_signal(bullish_indicators())

    assert "order_id" not in result
    assert "order_sent" not in result

