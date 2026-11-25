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

def calculate_position_size(req: RiskRequest) -> dict:
    values=(req.balance,req.risk_percent,req.entry_price,req.stop_loss,req.tick_size,req.tick_value_per_lot,req.min_lot,req.lot_step,req.max_lot)
    if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not isfinite(v) for v in values):
        return {"status":"REJECT","reason":"Invalid numeric input."}
    if req.balance<=0 or not 0<req.risk_percent<=1:
        return {"status":"REJECT","reason":"Risk per trade must be greater than zero and at most 1 percent."}
    if min(req.entry_price,req.stop_loss,req.tick_size,req.tick_value_per_lot,req.min_lot,req.lot_step,req.max_lot)<=0:
        return {"status":"REJECT","reason":"Invalid price or broker contract specification."}
    if req.max_lot<req.min_lot:return {"status":"REJECT","reason":"Maximum lot is below minimum lot."}
    distance=abs(req.entry_price-req.stop_loss)
    if distance==0:return {"status":"REJECT","reason":"Stop loss must differ from entry."}
    budget=req.balance*req.risk_percent/100
    risk_per_lot=(distance/req.tick_size)*req.tick_value_per_lot
    raw=budget/risk_per_lot
    lots=min(floor((raw+1e-12)/req.lot_step)*req.lot_step,req.max_lot)
    if lots+1e-12<req.min_lot:
        return {"status":"REJECT","reason":"Minimum broker lot would exceed configured risk budget.","risk_budget":round(budget,8),"raw_lots":round(raw,8),"minimum_lot":req.min_lot,"estimated_minimum_lot_risk":round(req.min_lot*risk_per_lot,8)}
    risk=lots*risk_per_lot
    return {"status":"ACCEPT_FOR_REVIEW","lots":round(lots,8),"risk_budget":round(budget,8),"estimated_risk":round(risk,8),"stop_distance":round(distance,8),"note":"Estimated risk excludes spread, commission and slippage; validate live broker contract data."}
