
import pytest

from risk_management.trade_levels import calculate_trade_levels


def test_buy_trade_levels():
    result = calculate_trade_levels(
        entry_price=4000,
        atr_value=10,
        direction="BUY",
    )

    assert result["status"] == "CALCULATED"
    assert result["stop_loss"] == 3985
    assert result["take_profit"] == 4030
    assert result["stop_distance"] == 15
    assert result["reward_distance"] == 30


def test_sell_trade_levels():
    result = calculate_trade_levels(
        entry_price=4000,
        atr_value=10,
        direction="SELL",
    )

    assert result["status"] == "CALCULATED"
    assert result["stop_loss"] == 4015
    assert result["take_profit"] == 3970


def test_custom_atr_multiplier():
    result = calculate_trade_levels(
        entry_price=4000,
        atr_value=10,
        direction="BUY",
        atr_multiplier=2,
    )

    assert result["stop_distance"] == 20
    assert result["stop_loss"] == 3980


def test_custom_risk_reward():
    result = calculate_trade_levels(
        entry_price=4000,
        atr_value=10,
        direction="BUY",
        risk_reward=3,
    )

    assert result["reward_distance"] == 45
    assert result["take_profit"] == 4045


@pytest.mark.parametrize(
    "direction",
    ["INVALID", "", None, 123],
)
def test_invalid_direction(direction):
    result = calculate_trade_levels(
        entry_price=4000,
        atr_value=10,
        direction=direction,
    )

    assert result["status"] == "REJECTED"
    assert result["reason"] == "INVALID_DIRECTION"


@pytest.mark.parametrize(
    "atr_value",
    [0, -1, float("nan"), float("inf"), True, None],
)
def test_invalid_atr(atr_value):
    result = calculate_trade_levels(
        entry_price=4000,
        atr_value=atr_value,
        direction="BUY",
    )

    assert result["status"] == "REJECTED"


def test_invalid_entry_price():
    result = calculate_trade_levels(
        entry_price=0,
        atr_value=10,
        direction="BUY",
    )

    assert result["status"] == "REJECTED"
    assert result["reason"] == "INVALID_ENTRY_PRICE"


def test_invalid_atr_multiplier():
    result = calculate_trade_levels(
        entry_price=4000,
        atr_value=10,
        direction="BUY",
        atr_multiplier=0,
    )

    assert result["status"] == "REJECTED"
    assert result["reason"] == "INVALID_ATR_MULTIPLIER"


def test_invalid_risk_reward():
    result = calculate_trade_levels(
        entry_price=4000,
        atr_value=10,
        direction="BUY",
        risk_reward=0,
    )

    assert result["status"] == "REJECTED"
    assert result["reason"] == "INVALID_RISK_REWARD"


def test_reject_non_positive_calculated_price():
    result = calculate_trade_levels(
        entry_price=10,
        atr_value=10,
        direction="BUY",
    )

    assert result["status"] == "REJECTED"
    assert result["reason"] == "INVALID_CALCULATED_PRICE"

