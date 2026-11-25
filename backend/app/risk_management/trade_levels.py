from math import isfinite
DEFAULT_ATR_MULTIPLIER=1.5
DEFAULT_RISK_REWARD=2.0
def calculate_trade_levels(entry_price,atr_value,direction,atr_multiplier=1.5,risk_reward=2.0):
    for name,value in {"entry_price":entry_price,"atr_value":atr_value,"atr_multiplier":atr_multiplier,"risk_reward":risk_reward}.items():
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not isfinite(value):
            return {"status":"REJECTED","reason":"INVALID_"+name.upper()}
    direction=direction.strip().upper() if isinstance(direction,str) else ""
    if entry_price<=0:return {"status":"REJECTED","reason":"INVALID_ENTRY_PRICE"}
    if atr_value<=0:return {"status":"REJECTED","reason":"INVALID_ATR"}
    if atr_multiplier<=0:return {"status":"REJECTED","reason":"INVALID_ATR_MULTIPLIER"}
    if risk_reward<=0:return {"status":"REJECTED","reason":"INVALID_RISK_REWARD"}
    if direction not in ("BUY","SELL"):return {"status":"REJECTED","reason":"INVALID_DIRECTION"}
    distance=atr_value*atr_multiplier; reward=distance*risk_reward
    sl,tp=(entry_price-distance,entry_price+reward) if direction=="BUY" else (entry_price+distance,entry_price-reward)
    if sl<=0 or tp<=0:return {"status":"REJECTED","reason":"INVALID_CALCULATED_PRICE"}
    return {"status":"CALCULATED","direction":direction,"entry_price":entry_price,"atr_value":atr_value,
            "atr_multiplier":atr_multiplier,"risk_reward":risk_reward,"stop_distance":distance,
            "reward_distance":reward,"stop_loss":sl,"take_profit":tp}
