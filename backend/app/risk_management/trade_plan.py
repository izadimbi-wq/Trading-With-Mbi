from dataclasses import dataclass
from math import isfinite
from risk_management.sizing import RiskRequest,calculate_position_size
from risk_management.trade_levels import calculate_trade_levels
@dataclass
class TradePlanRequest:
    balance:float; risk_percent:float; entry_price:float; atr_value:float; direction:str
    tick_size:float; tick_value_per_lot:float; min_lot:float; lot_step:float; max_lot:float
def create_trade_plan(req):
    vals={k:getattr(req,k) for k in ("balance","risk_percent","entry_price","atr_value","tick_size","tick_value_per_lot","min_lot","lot_step","max_lot")}
    if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not isfinite(v) for v in vals.values()):
        return {"status":"REJECT","reason":"Invalid numeric request."}
    if req.balance<=0 or not 0<req.risk_percent<=1:return {"status":"REJECT","reason":"Risk must be greater than zero and at most 1%."}
    levels=calculate_trade_levels(req.entry_price,req.atr_value,req.direction,1.5,2.0)
    if levels["status"]!="CALCULATED":return {"status":"REJECT","reason":"Trade levels rejected.","details":levels}
    sizing=calculate_position_size(RiskRequest(req.balance,req.risk_percent,req.entry_price,levels["stop_loss"],
        req.tick_size,req.tick_value_per_lot,req.min_lot,req.lot_step,req.max_lot))
    if sizing["status"]!="ACCEPT_FOR_REVIEW":return {"status":"REJECT","reason":"Position size violates risk budget.","levels":levels,"sizing":sizing}
    return {"status":"ACCEPT_FOR_REVIEW",**levels,"lots":sizing["lots"],"risk_budget":sizing["risk_budget"],
            "estimated_risk":sizing["estimated_risk"],"note":"Estimated risk excludes fees/slippage unless supplied. No order executed."}
