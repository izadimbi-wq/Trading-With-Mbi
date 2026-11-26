from math import isfinite
from .indicators import ema,rsi,atr,macd,ichimoku
from .signal_engine import generate_signal
from .levels import support_resistance,pullback_zone

SUPPORTED_SYMBOLS={"XAUUSD","EURUSD","XAGUSD"}
SUPPORTED_TIMEFRAMES={"M1","M5","M15","M30","H1","H4","D1"}
SETTINGS={"ema_fast":20,"ema_slow":50,"rsi":14,"atr":14,"macd_fast":12,"macd_slow":26,"macd_signal":9,
          "tenkan":9,"kijun":26,"senkou_b":52,"displacement":26}

def validate_market_input(symbol,timeframe,candles):
    symbol=str(symbol).upper(); timeframe=str(timeframe).upper()
    if symbol not in SUPPORTED_SYMBOLS: raise ValueError("Unsupported trading symbol.")
    if timeframe not in SUPPORTED_TIMEFRAMES: raise ValueError("Unsupported timeframe.")
    if not isinstance(candles,list) or not candles: raise ValueError("Candles must be a non-empty list.")
    required=("open","high","low","close")
    for idx,c in enumerate(candles):
        if not isinstance(c,dict) or not all(k in c for k in required): raise ValueError(f"Incomplete candle {idx}.")
        if c.get("isOpen") is True: raise ValueError("Open candles must be excluded.")
        vals=[c[k] for k in required]
        if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not isfinite(v) or v<=0 for v in vals): raise ValueError(f"Invalid candle {idx}.")
        if c["high"]<max(c["open"],c["close"]) or c["low"]>min(c["open"],c["close"]) or c["high"]<c["low"]: raise ValueError(f"Invalid OHLC candle {idx}.")
    return {"symbol":symbol,"timeframe":timeframe,"candles":candles}

def calculate_indicators(candles):
    s=SETTINGS; cl=[x["close"] for x in candles]; hi=[x["high"] for x in candles]; lo=[x["low"] for x in candles]
    required=max(s["ema_slow"],s["rsi"]+1,s["atr"]+1,s["macd_slow"]+s["macd_signal"]-1,s["senkou_b"]+s["displacement"])
    if len(candles)<required:return {"status":"INSUFFICIENT_DATA","required_candles":required,"available_candles":len(candles)}
    vals={"ema":{"fast":ema(cl,s["ema_fast"]),"slow":ema(cl,s["ema_slow"]),"fast_period":s["ema_fast"],"slow_period":s["ema_slow"]},
          "rsi":{"period":s["rsi"],"value":rsi(cl,s["rsi"])},"atr":{"period":s["atr"],"value":atr(hi,lo,cl,s["atr"])},
          "macd":macd(cl,s["macd_fast"],s["macd_slow"],s["macd_signal"]),
          "ichimoku":ichimoku(hi,lo,cl,s["tenkan"],s["kijun"],s["senkou_b"],s["displacement"])}
    return {"status":"CALCULATED","candles_used":len(candles),"indicators":vals}

def analyze_market(symbol,timeframe,candles,account=None,contract=None):
    v=validate_market_input(symbol,timeframe,candles); data=v["candles"]; result=calculate_indicators(data)
    result.update({"symbol":v["symbol"],"timeframe":v["timeframe"]})
    if result["status"]!="CALCULATED":
        result.update({"signal":"NO TRADE","signal_status":"INSUFFICIENT_DATA","signal_reason":"Not enough closed candles."})
        return result
    indicators=result["indicators"]; sig=generate_signal(indicators)
    result.update({"signal":sig["signal"],"signal_status":sig["status"],"signal_reason":sig["reason"],"signal_details":sig,
                   "trend":"BULLISH" if indicators["ema"]["fast"]>indicators["ema"]["slow"] else "BEARISH" if indicators["ema"]["fast"]<indicators["ema"]["slow"] else "NEUTRAL",
                   "support_resistance":support_resistance(data,indicators["atr"]["value"]),
                   "pullback":pullback_zone(data,indicators["atr"]["value"]),
                   "entry_price":data[-1]["close"],
                   "note":"Closed-candle analysis only. No order is sent. S/R and pullback are estimates."})
    result["trade_plan"]={"status":"NOT_REQUESTED"}
    if sig["signal"] in ("BUY","SELL") and account and contract:
        from risk_management.trade_plan import TradePlanRequest,create_trade_plan
        plan=create_trade_plan(TradePlanRequest(balance=account["balance"],risk_percent=account.get("risk_percent",1),
            entry_price=data[-1]["close"],atr_value=indicators["atr"]["value"],direction=sig["signal"],
            tick_size=contract["tick_size"],tick_value_per_lot=contract["tick_value_per_lot"],
            min_lot=contract["min_lot"],lot_step=contract["lot_step"],max_lot=contract["max_lot"]))
        result["trade_plan"]=plan
        if plan["status"]!="ACCEPT_FOR_REVIEW":
            result["signal"]="NO TRADE"; result["signal_status"]="RISK_REJECTED"
            result["signal_reason"]="Signal rejected by risk controls: "+plan.get("reason","")
    elif sig["signal"] in ("BUY","SELL"):
        result["trade_plan"]={"status":"UNAVAILABLE","reason":"Live broker contract specifications and account balance are required."}
    return result
