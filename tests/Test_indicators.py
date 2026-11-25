ا

import pytest

from technical_analysis.indicators import ema, rsi, atr


def test_ema_calculation():
    prices = [10, 11, 12, 13, 14]
    result = ema(prices, 3)

    assert result == pytest.approx(13.0)


def test_ema_insufficient_data():
    assert ema([10, 11], 3) is None


def test_rsi_all_gains():
    prices = list(range(1, 20))
    assert rsi(prices, 14) == 100.0


def test_rsi_all_losses():
    prices = list(range(20, 1, -1))
    assert rsi(prices, 14) == 0.0


def test_rsi_insufficient_data():
    assert rsi([10, 11, 12], 14) is None


def test_atr_calculation():
    highs = [11, 12, 13, 14]
    lows = [9, 10, 11, 12]
    closes = [10, 11, 12, 13]

    result = atr(highs, lows, closes, 2)

    assert result == pytest.approx(2.0)


def test_atr_insufficient_data():
    assert atr(
        [11, 12],
        [9, 10],
        [10, 11],
        14
    ) is None


def test_invalid_period():
    with pytest.raises(ValueError):
        ema([10, 11, 12], 0)


def test_invalid_prices():
    with pytest.raises(ValueError):
        ema([10, -1, 12], 2)

from technical_analysis.indicators import macd


def test_macd_calculation():
    prices = [float(i) for i in range(1, 101)]

    result = macd(prices)

    assert result is not None
    assert "macd" in result
    assert "signal" in result
    assert "histogram" in result

    assert result["macd"] > 0
    assert result["histogram"] == pytest.approx(
        result["macd"] - result["signal"]
    )


def test_macd_insufficient_data():
    prices = [float(i) for i in range(1, 30)]

    assert macd(prices) is None


def test_macd_invalid_periods():
    prices = [float(i) for i in range(1, 101)]

    with pytest.raises(ValueError):
        macd(prices, fast=26, slow=12)
def test_macd_negative_values():
    prices = [100.0 - i for i in range(100)]

    result = macd(prices)

    assert result is not None
    assert result["macd"] < 0
    assert result["signal"] < 0


def test_macd_histogram_calculation():
    prices = [100.0 - i for i in range(100)]

    result = macd(prices)

    assert result is not None
    assert result["histogram"] == pytest.approx(
        result["macd"] - result["signal"]
    )
