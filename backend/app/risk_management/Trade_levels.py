
from math import isfinite


DEFAULT_ATR_MULTIPLIER = 1.5
DEFAULT_RISK_REWARD = 2.0


def calculate_trade_levels(
    entry_price,
    atr_value,
    direction,
    atr_multiplier=DEFAULT_ATR_MULTIPLIER,
    risk_reward=DEFAULT_RISK_REWARD,
):
    """
    Calculate stop-loss and take-profit levels using ATR.

    BUY:
        Stop loss below entry.
        Take profit above entry.

    SELL:
        Stop loss above entry.
        Take profit below entry.

    This function only calculates trade levels.
    It does not execute orders or approve a trade.
    """

    numeric_values = {
        "entry_price": entry_price,
        "atr_value": atr_value,
        "atr_multiplier": atr_multiplier,
        "risk_reward": risk_reward,
    }

    for name, value in numeric_values.items():
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not isfinite(value)
        ):
            return {
                "status": "REJECTED",
                "reason": f"INVALID_{name.upper()}",
            }

    if entry_price <= 0:
        return {
            "status": "REJECTED",
            "reason": "INVALID_ENTRY_PRICE",
        }

    if atr_value <= 0:
        return {
            "status": "REJECTED",
            "reason": "INVALID_ATR",
        }

    if atr_multiplier <= 0:
        return {
            "status": "REJECTED",
            "reason": "INVALID_ATR_MULTIPLIER",
        }

    if risk_reward <= 0:
        return {
            "status": "REJECTED",
            "reason": "INVALID_RISK_REWARD",
        }

    if not isinstance(direction, str):
        return {
            "status": "REJECTED",
            "reason": "INVALID_DIRECTION",
        }

    direction = direction.strip().upper()

    if direction not in {"BUY", "SELL"}:
        return {
            "status": "REJECTED",
            "reason": "INVALID_DIRECTION",
        }

    stop_distance = atr_value * atr_multiplier
    reward_distance = stop_distance * risk_reward

    if direction == "BUY":
        stop_loss = entry_price - stop_distance
        take_profit = entry_price + reward_distance
    else:
        stop_loss = entry_price + stop_distance
        take_profit = entry_price - reward_distance

    if stop_loss <= 0 or take_profit <= 0:
        return {
            "status": "REJECTED",
            "reason": "INVALID_CALCULATED_PRICE",
        }

    return {
        "status": "CALCULATED",
        "direction": direction,
        "entry_price": entry_price,
        "atr_value": atr_value,
        "atr_multiplier": atr_multiplier,
        "risk_reward": risk_reward,
        "stop_distance": stop_distance,
        "reward_distance": reward_distance,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
    }

