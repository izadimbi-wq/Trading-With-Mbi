import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.risk_management.sizing import RiskRequest, calculate_position_size

def test_rejects_when_minimum_lot_exceeds_budget():
    req = RiskRequest(
        balance=50, risk_percent=0.5, entry_price=2000, stop_loss=1990,
        tick_size=0.01, tick_value_per_lot=1.0,
        min_lot=0.01, lot_step=0.01, max_lot=100
    )
    result = calculate_position_size(req)
    assert result["status"] == "REJECT"

def test_rounds_down_to_lot_step():
    req = RiskRequest(
        balance=1000, risk_percent=1, entry_price=1.1, stop_loss=1.099,
        tick_size=0.0001, tick_value_per_lot=1.0,
        min_lot=0.01, lot_step=0.01, max_lot=100
    )
    result = calculate_position_size(req)
    assert result["status"] == "ACCEPT_FOR_REVIEW"
    assert result["lots"] == 10.0
