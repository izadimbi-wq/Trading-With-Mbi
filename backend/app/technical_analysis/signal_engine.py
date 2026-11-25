from math import isfinite

def _no_trade(status,reason,buy=None,sell=None):
    return {"signal":"NO TRADE","status":status,"reason":reason,
            "buy_confirmations":buy or [],"sell_confirmations":sell or [],
            "required_confirmations":5,"score":0}

def generate_signal(indicators):
    if not isinstance(indicators,dict): raise ValueError("Indicators must be a dictionary.")
    keys=("ema","rsi","atr","macd","ichimoku")
    if any(k not in indicators for k in keys): raise ValueError("Required indicators are missing.")
    e,r,a,m,i=(indicators[k] for k in keys)
    if not all(isinstance(x,dict) for x in (e,r,a,m,i)): raise ValueError("Invalid indicator structure.")
    vals=(e.get("fast"),e.get("slow"),r.get("value"),a.get("value"),m.get("macd"),m.get("signal"))
    if any(isinstance(x,bool) or not isinstance(x,(int,float)) or not isfinite(x) for x in vals):
        return _no_trade("INVALID_INDICATOR_DATA","Indicator values are missing or invalid.")
    ef,es,rv,av,ml,sl=vals
    if ef<=0 or es<=0 or av<=0 or not 0<=rv<=100:
        return _no_trade("INVALID_INDICATOR_DATA","Indicator values are outside valid ranges.")
    cloud=i.get("price_vs_cloud"); bias=i.get("tenkan_kijun_bias")
    if cloud not in ("ABOVE","BELOW","INSIDE") or bias not in ("BULLISH","BEARISH","NEUTRAL"):
        return _no_trade("INSUFFICIENT_DATA","Ichimoku confirmation is unavailable.")
    buy=[]; sell=[]
    if ef>es: buy.append("EMA_BULLISH")
    elif ef<es: sell.append("EMA_BEARISH")
    if cloud=="ABOVE": buy.append("PRICE_ABOVE_CLOUD")
    elif cloud=="BELOW": sell.append("PRICE_BELOW_CLOUD")
    if bias=="BULLISH": buy.append("TENKAN_ABOVE_KIJUN")
    elif bias=="BEARISH": sell.append("TENKAN_BELOW_KIJUN")
    if ml>sl: buy.append("MACD_BULLISH")
    elif ml<sl: sell.append("MACD_BEARISH")
    if 50<rv<70: buy.append("RSI_BULLISH")
    elif 30<rv<50: sell.append("RSI_BEARISH")
    direction="BUY" if len(buy)==5 else "SELL" if len(sell)==5 else "NO TRADE"
    count=max(len(buy),len(sell))
    return {"signal":direction,"status":"SIGNAL_GENERATED" if direction!="NO TRADE" else "NO_VALID_SETUP",
            "reason":"All five confirmations agree." if direction!="NO TRADE" else "Required confirmations do not fully agree.",
            "buy_confirmations":buy,"sell_confirmations":sell,"required_confirmations":5,
            "score":count,"score_percent":count*20,
            "note":"Score is confirmation coverage, not a win probability. Chikou is not a signal condition."}
