
from dataclasses import dataclass
from math import isfinite

from risk_management.sizing import (
    RiskRequest,
    calculate_position_size,
)
from risk_management.trade_levels import calculate_trade_levels


@dataclass
class TradePlanRequest:
    balance: float
    risk_percent: float
    entry_price: float
    atr_value: float
    direction: str

    tick_size: float
    tick_value_per_lot: float
    min_lot: float
    lot_step: float
    max_lot: float


def create_trade_plan(req: TradePlanRequest) -> dict:
    """
    Build a risk-controlled trade plan.

    Maximum configured risk: 1 percent.
    Stop loss: 1.5 ATR.
    Take profit: 2 times stop distance.

    This function does not execute orders.
    """

    numeric_fields = {
        "balance": req.balance,
        "risk_percent": req.risk_percent,
        "entry_price": req.entry_price,
        "atr_value": req.atr_value,
        "tick_size": req.tick_size,
        "tick_value_per_lot": req.tick_value_per_lot,
        "min_lot": req.min_lot,
        "lot_step": req.lot_step,
        "max_lot": req.max_lot,
    }

    for name, value in numeric_fields.items():
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not isfinite(value)
        ):
            return {
                "status": "REJECT",
                "reason": f"Invalid numeric field: {name}.",
            }

    if req.balance <= 0:
        return {
            "status": "REJECT",
            "reason": "Balance must be greater than zero.",
        }

    if not 0 < req.risk_percent <= 1:
        return {
            "status": "REJECT",
            "reason": "Risk per trade cannot exceed 1 percent.",
        }

    levels = calculate_trade_levels(
        entry_price=req.entry_price,
        atr_value=req.atr_value,
        direction=req.direction,
        atr_multiplier=1.5,
        risk_reward=2.0,
    )

    if levels["status"] != "CALCULATED":
        return {
            "status": "REJECT",
            "reason": "Trade levels could not be calculated.",
            "details": levels,
        }

    sizing_request = RiskRequest(
        balance=req.balance,
        risk_percent=req.risk_percent,
        entry_price=req.entry_price,
        stop_loss=levels["stop_loss"],
        tick_size=req.tick_size,
        tick_value_per_lot=req.tick_value_per_lot,
        min_lot=req.min_lot,
        lot_step=req.lot_step,
        max_lot=req.max_lot,
    )

    sizing = calculate_position_size(sizing_request)

    if sizing["status"] != "ACCEPT_FOR_REVIEW":
        return {
            "status": "REJECT",
            "reason": "Position size does not satisfy risk limits.",
            "levels": levels,
            "sizing": sizing,
        }

    return {
        "status": "ACCEPT_FOR_REVIEW",
        "direction": levels["direction"],
        "entry_price": levels["entry_price"],
        "stop_loss": levels["stop_loss"],
        "take_profit": levels["take_profit"],
        "atr_value": levels["atr_value"],
        "atr_multiplier": levels["atr_multiplier"],
        "risk_reward": levels["risk_reward"],
        "stop_distance": levels["stop_distance"],
        "reward_distance": levels["reward_distance"],
        "lots": sizing["lots"],
        "risk_budget": sizing["risk_budget"],
        "estimated_risk": sizing["estimated_risk"],
        "note": (
            "Trade plan calculated. Broker data must be revalidated. "
            "No order has been executed."
        ),
    }
