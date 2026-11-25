from math import isfinite

def support_resistance(candles, atr_value=None, left=3, right=3, max_levels=3):
    """Confirmed pivots only; right-side candles must already be closed."""
    if not isinstance(candles,list) or len(candles)<left+right+3:
        return {"supports":[],"resistances":[],"status":"INSUFFICIENT_DATA"}
    highs=[float(x["high"]) for x in candles]; lows=[float(x["low"]) for x in candles]
    closes=[float(x["close"]) for x in candles]; last=closes[-1]
    tolerance=max((atr_value or 0)*0.25, last*0.0002)
    pivots=[]
    for i in range(left,len(candles)-right):
        if highs[i]>=max(highs[i-left:i+right+1]):
            pivots.append(("resistance",highs[i],i))
        if lows[i]<=min(lows[i-left:i+right+1]):
            pivots.append(("support",lows[i],i))
    def cluster(kind):
        groups=[]
        for _,price,index in [p for p in pivots if p[0]==kind]:
            found=next((g for g in groups if abs(g["price"]-price)<=tolerance),None)
            if found is None: groups.append({"price":price,"touches":1,"last_index":index})
            else:
                n=found["touches"]; found["price"]=(found["price"]*n+price)/(n+1)
                found["touches"]+=1; found["last_index"]=max(found["last_index"],index)
        for g in groups:
            g["strength"]="STRONG" if g["touches"]>=3 else "MODERATE" if g["touches"]==2 else "WEAK"
            g["distance"]=abs(last-g["price"])
        return sorted(groups,key=lambda g:g["distance"])[:max_levels]
    return {"status":"CALCULATED","supports":cluster("support"),"resistances":cluster("resistance"),
            "method":"Confirmed swing pivots clustered by ATR/price tolerance; levels are probabilistic."}

def pullback_zone(candles, atr_value=None):
    if len(candles)<12: return {"status":"INSUFFICIENT_DATA","zone":None}
    # Latest confirmed major swing endpoints; only confirmed pivots.
    highs=[float(x["high"]) for x in candles]; lows=[float(x["low"]) for x in candles]
    closes=[float(x["close"]) for x in candles]
    hi=max(range(len(highs)-3),key=lambda j:highs[j]); lo=min(range(len(lows)-3),key=lambda j:lows[j])
    if hi<lo:
        direction="BULLISH"; start=lows[lo]; end=highs[hi]
        if end<=start:return {"status":"UNAVAILABLE","zone":None}
        a=end-(end-start)*0.618; b=end-(end-start)*0.382
    else:
        direction="BEARISH"; start=highs[hi]; end=lows[lo]
        if start<=end:return {"status":"UNAVAILABLE","zone":None}
        a=end+(start-end)*0.382; b=end+(start-end)*0.618
    return {"status":"ESTIMATED","direction":direction,"zone":{"lower":min(a,b),"upper":max(a,b)},
            "method":"38.2%-61.8% retracement of latest swing; probabilistic, not a reversal guarantee."}
