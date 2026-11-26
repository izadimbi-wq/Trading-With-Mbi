from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from risk_management.sizing import calculate_position_size, RiskRequest
from risk_management.trade_plan import TradePlanRequest, create_trade_plan
from technical_analysis.strategy import analyze_market
from market_data.biquote_client import get_tick, get_ohlc, MarketDataError

app=FastAPI(title="TradingAI API",version="0.3.0")
SUPPORTED_SYMBOLS=["XAUUSD","EURUSD","XAGUSD"]

class RiskPayload(BaseModel):
    balance:float=Field(gt=0)
    risk_percent:float=Field(gt=0,le=1)
    entry_price:float=Field(gt=0)
    stop_loss:float=Field(gt=0)
    tick_size:float=Field(gt=0)
    tick_value_per_lot:float=Field(gt=0)
    min_lot:float=Field(gt=0)
    lot_step:float=Field(gt=0)
    max_lot:float=Field(gt=0)

class ContractPayload(BaseModel):
    tick_size:float=Field(gt=0)
    tick_value_per_lot:float=Field(gt=0)
    min_lot:float=Field(gt=0)
    lot_step:float=Field(gt=0)
    max_lot:float=Field(gt=0)

class AnalysisPayload(BaseModel):
    symbol:str
    timeframe:str="M5"
    candles:list[dict]
    balance:float|None=Field(default=None,gt=0)
    risk_percent:float=Field(default=1,gt=0,le=1)
    contract:ContractPayload|None=None

@app.get("/health")
def health():return {"status":"ok","service":"TradingAI API","mode":"analysis-and-market-data"}

@app.get("/api/v1/market/snapshot")
def market_snapshot():
    results={}
    for symbol in SUPPORTED_SYMBOLS:
        try:results[symbol]={"status":"ok","data":get_tick(symbol)}
        except MarketDataError as exc:results[symbol]={"status":"unavailable","message":str(exc)}
    available=sum(1 for x in results.values() if x["status"]=="ok")
    return {"provider":"biquote","status":"ok" if available==len(SUPPORTED_SYMBOLS) else "partial" if available else "unavailable","symbols":results}

@app.get("/api/v1/market/{symbol}/tick")
def market_tick(symbol:str):
    symbol=symbol.upper()
    if symbol not in SUPPORTED_SYMBOLS:raise HTTPException(400,"Unsupported symbol.")
    try:return get_tick(symbol)
    except MarketDataError as exc:raise HTTPException(502,str(exc))

@app.get("/api/v1/market/{symbol}/ohlc")
def market_ohlc(symbol:str,interval:str=Query(default="5m"),limit:int=Query(default=100,ge=1,le=1000)):
    symbol=symbol.upper()
    if symbol not in SUPPORTED_SYMBOLS:raise HTTPException(400,"Unsupported symbol.")
    try:return get_ohlc(symbol,interval,limit)
    except MarketDataError as exc:raise HTTPException(502,str(exc))

@app.post("/api/v1/risk/position-size")
def position_size(payload:RiskPayload):return calculate_position_size(RiskRequest(**payload.model_dump()))

@app.post("/api/v1/analysis")
def analysis(payload:AnalysisPayload):
    if payload.symbol.upper() not in SUPPORTED_SYMBOLS:raise HTTPException(400,"Unsupported symbol.")
    account={"balance":payload.balance,"risk_percent":payload.risk_percent} if payload.balance is not None else None
    contract=payload.contract.model_dump() if payload.contract is not None else None
    try:return analyze_market(payload.symbol,payload.timeframe,payload.candles,account,contract)
    except ValueError as exc:raise HTTPException(422,str(exc))
