

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
