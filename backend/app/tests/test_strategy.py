import pytest
from technical_analysis.strategy import validate_market_input,analyze_market

def candles(n=100):
    out=[]
    for i in range(n):
        c=2000+i*0.2
        out.append({"open":c-0.1,"high":c+1,"low":c-1,"close":c})
    return out

def test_valid_input(): assert validate_market_input("xauusd","m5",candles(2))["symbol"]=="XAUUSD"
def test_reject_open_candle():
    x=candles();x[-1]["isOpen"]=True
    with pytest.raises(ValueError):analyze_market("XAUUSD","M5",x)
def test_full_analysis_returns_new_signal_contract():
    x=analyze_market("XAUUSD","M5",candles())
    assert x["status"]=="CALCULATED"
    assert x["signal"] in ("BUY","SELL","NO TRADE")
    assert "support_resistance" in x and "pullback" in x
def test_insufficient_data():
    x=analyze_market("XAUUSD","M5",candles(77))
    assert x["signal"]=="NO TRADE" and x["status"]=="INSUFFICIENT_DATA"
