from risk_management.trade_plan import TradePlanRequest,create_trade_plan
def test_minimum_lot_risk_rejected():
    r=TradePlanRequest(50,1,2000,10,"BUY",0.01,1,0.01,0.01,100)
    assert create_trade_plan(r)["status"]=="REJECT"
def test_invalid_risk_rejected():
    r=TradePlanRequest(50,1.1,2000,10,"BUY",0.01,1,0.01,0.01,100)
    assert create_trade_plan(r)["status"]=="REJECT"
