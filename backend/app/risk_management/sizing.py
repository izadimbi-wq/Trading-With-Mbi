from dataclasses import dataclass, asdict
from math import floor

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

def calculate_position_size(req: RiskRequest) -> dict:
    if req.balance <= 0 or not (0 < req.risk_percent <= 1):
        return {"status": "REJECT", "reason": "Invalid balance or risk percentage."}
    if req.entry_price <= 0 or req.stop_loss <= 0 or req.tick_size <= 0:
        return {"status": "REJECT", "reason": "Invalid price or tick specification."}
    if req.tick_value_per_lot <= 0 or req.min_lot <= 0 or req.lot_step <= 0:
        return {"status": "REJECT", "reason": "Invalid broker contract specification."}

    distance = abs(req.entry_price - req.stop_loss)
    if distance == 0:
        return {"status": "REJECT", "reason": "Stop loss must differ from entry."}

    risk_budget = req.balance * req.risk_percent / 100.0
    ticks = distance / req.tick_size
    risk_per_lot = ticks * req.tick_value_per_lot
    raw_lots = risk_budget / risk_per_lot

    # Round DOWN to lot step. Never round upward to broker minimum.
    stepped_lots = floor((raw_lots + 1e-12) / req.lot_step) * req.lot_step
    stepped_lots = min(stepped_lots, req.max_lot)

    if stepped_lots + 1e-12 < req.min_lot:
        min_lot_risk = req.min_lot * risk_per_lot
        return {
            "status": "REJECT",
            "reason": "Minimum broker lot would exceed the configured risk budget.",
            "risk_budget": round(risk_budget, 8),
            "raw_lots": round(raw_lots, 8),
            "minimum_lot": req.min_lot,
            "estimated_minimum_lot_risk": round(min_lot_risk, 8)
        }

    estimated_risk = stepped_lots * risk_per_lot
    return {
        "status": "ACCEPT_FOR_REVIEW",
        "lots": round(stepped_lots, 8),
        "risk_budget": round(risk_budget, 8),
        "estimated_risk": round(estimated_risk, 8),
        "stop_distance": round(distance, 8),
        "note": "Revalidate tick value, spread, commission, slippage and margin with live broker data."
    }
