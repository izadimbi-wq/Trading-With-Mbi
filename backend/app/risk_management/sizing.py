
from dataclasses import dataclass
from math import floor, isfinite


@dataclass
class RiskRequest:
    balance: float
    risk_percent: float
    entry_price: float
    stop_loss: float
    tick_size: float
    tick_value_per_lot: float
    min_lot: float
    lot_step: float
    max_lot: float
    direction: str = ""
    commission_per_lot: float = 0.0
    slippage_ticks: float = 0.0


def calculate_position_size(req: RiskRequest) -> dict:
    values = (
        req.balance,
        req.risk_percent,
        req.entry_price,
        req.stop_loss,
        req.tick_size,
        req.tick_value_per_lot,
        req.min_lot,
        req.lot_step,
        req.max_lot,
        req.commission_per_lot,
        req.slippage_ticks,
    )

    if any(
        isinstance(v, bool)
        or not isinstance(v, (int, float))
        or not isfinite(v)
        for v in values
    ):
        return {
            "status": "REJECT",
            "reason": "Invalid numeric input."
        }

    if req.balance <= 0 or not 0 < req.risk_percent <= 1:
        return {
            "status": "REJECT",
            "reason": "Risk must be greater than 0 and at most 1 percent."
        }

    if min(
        req.entry_price,
        req.stop_loss,
        req.tick_size,
        req.tick_value_per_lot,
        req.min_lot,
        req.lot_step,
        req.max_lot,
    ) <= 0:
        return {
            "status": "REJECT",
            "reason": "Invalid broker contract specification."
        }

    if req.commission_per_lot < 0 or req.slippage_ticks < 0:
        return {
            "status": "REJECT",
            "reason": "Invalid commission or slippage."
        }

    direction = req.direction.upper().strip()

    if direction == "BUY" and req.stop_loss >= req.entry_price:
        return {
            "status": "REJECT",
            "reason": "BUY stop loss must be below entry price."
        }

    if direction == "SELL" and req.stop_loss <= req.entry_price:
        return {
            "status": "REJECT",
            "reason": "SELL stop loss must be above entry price."
        }

    if direction and direction not in ("BUY", "SELL"):
        return {
            "status": "REJECT",
            "reason": "Direction must be BUY or SELL."
        }

    if req.max_lot < req.min_lot:
        return {
            "status": "REJECT",
            "reason": "Maximum lot is below minimum lot."
        }

    distance = abs(req.entry_price - req.stop_loss)

    if distance <= 0:
        return {
            "status": "REJECT",
            "reason": "Stop loss must differ from entry."
        }

    risk_budget = req.balance * req.risk_percent / 100.0

    price_risk_per_lot = (
        distance / req.tick_size
    ) * req.tick_value_per_lot

    slippage_cost = (
        req.slippage_ticks * req.tick_value_per_lot
    )

    risk_per_lot = (
        price_risk_per_lot
        + slippage_cost
        + req.commission_per_lot
    )

    if risk_per_lot <= 0:
        return {
            "status": "REJECT",
            "reason": "Invalid calculated risk per lot."
        }

    raw_lots = risk_budget / risk_per_lot

    # Never round volume upward.
    max_steps = floor(
        (req.max_lot + 1e-12) / req.lot_step
    )

    raw_steps = floor(
        (raw_lots + 1e-12) / req.lot_step
    )

    allowed_steps = min(raw_steps, max_steps)
    lots = allowed_steps * req.lot_step

    if lots + 1e-12 < req.min_lot:
        return {
            "status": "REJECT",
            "reason": (
                "Minimum broker lot would exceed "
                "the configured risk budget."
            ),
            "risk_budget": round(risk_budget, 8),
            "raw_lots": round(raw_lots, 8),
            "minimum_lot": req.min_lot,
            "estimated_minimum_lot_risk": round(
                req.min_lot * risk_per_lot, 8
            ),
        }

    estimated_risk = lots * risk_per_lot

    if estimated_risk > risk_budget + 1e-10:
        return {
            "status": "REJECT",
            "reason": "Calculated risk exceeds risk budget."
        }

    return {
        "status": "ACCEPT_FOR_REVIEW",
        "direction": direction or None,
        "lots": round(lots, 8),
        "risk_budget": round(risk_budget, 8),
        "estimated_risk": round(estimated_risk, 8),
        "stop_distance": round(distance, 8),
        "price_risk_per_lot": round(price_risk_per_lot, 8),
        "commission_per_lot": req.commission_per_lot,
        "slippage_cost_per_lot": round(slippage_cost, 8),
        "note": (
            "Estimated risk includes configured commission "
            "and slippage assumptions. Live broker contract "
            "values must be verified."
        ),
    }
