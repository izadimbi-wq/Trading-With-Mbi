import os
from fastapi import FastAPI, HTTPException, Query, Header
from pydantic import BaseModel, Field
from risk_management.sizing import calculate_position_size, RiskRequest
from technical_analysis.strategy import analyze_market
from market_data.biquote_client import get_tick as get_biquote_tick, get_ohlc as get_biquote_ohlc, MarketDataError
from market_data import mt4_feed

app = FastAPI(title="TradingAI API", version="0.5.0-multisymbol")


class RiskPayload(BaseModel):
    balance: float = Field(gt=0)
    risk_percent: float = Field(gt=0, le=1)
    entry_price: float = Field(gt=0)
    stop_loss: float = Field(gt=0)
    tick_size: float = Field(gt=0)
    tick_value_per_lot: float = Field(gt=0)
    min_lot: float = Field(gt=0)
    lot_step: float = Field(gt=0)
    max_lot: float = Field(gt=0)


class ContractPayload(BaseModel):
    tick_size: float = Field(gt=0)
    tick_value_per_lot: float = Field(gt=0)
    min_lot: float = Field(gt=0)
    lot_step: float = Field(gt=0)
    max_lot: float = Field(gt=0)


class AnalysisPayload(BaseModel):
    symbol: str
    timeframe: str = "M5"
    candles: list[dict]
    balance: float | None = Field(default=None, gt=0)
    risk_percent: float = Field(default=1, gt=0, le=1)
    contract: ContractPayload | None = None
    contract_verified: bool = False
    provider: str = "mt4"


@app.get("/health")
def health():
    return {"status": "ok", "service": "TradingAI API",
            "mode": "analysis-and-market-data", "order_execution": False}


@app.post("/api/v1/mt4/market-data")
def mt4_market_data(payload: dict, x_tradingai_token: str | None = Header(default=None)):
    try:
        return mt4_feed.ingest(payload, x_tradingai_token)
    except PermissionError as exc:
        raise HTTPException(401, str(exc))
    except mt4_feed.MT4FeedError as exc:
        raise HTTPException(422, str(exc))


@app.get("/api/v1/market/symbols")
def market_symbols():
    return {"provider": "mt4", "symbols": mt4_feed.list_symbols()}


@app.get("/api/v1/market/snapshot")
def market_snapshot():
    results = {}
    for item in mt4_feed.list_symbols():
        symbol = item["symbol"]
        try:
            results[symbol] = {"status": "ok", "data": mt4_feed.get_quote(symbol)}
        except mt4_feed.MT4FeedError as exc:
            results[symbol] = {"status": "unavailable", "message": str(exc)}
    available = sum(1 for item in results.values() if item["status"] == "ok")
    status = "ok" if available and available == len(results) else "partial" if available else "unavailable"
    return {"provider": "mt4", "status": status, "symbols": results}


@app.get("/api/v1/market/{symbol}/tick")
def market_tick(symbol: str, provider: str = Query(default="mt4")):
    try:
        if provider.lower() == "mt4":
            return mt4_feed.get_quote(symbol)
        if provider.lower() == "biquote":
            return get_biquote_tick(symbol)
        raise HTTPException(400, "Unsupported market-data provider.")
    except mt4_feed.MT4FeedError as exc:
        raise HTTPException(503, str(exc))
    except MarketDataError as exc:
        raise HTTPException(502, str(exc))


@app.get("/api/v1/market/{symbol}/ohlc")
def market_ohlc(symbol: str, interval: str = Query(default="5m"),
                limit: int = Query(default=100, ge=1, le=1000),
                provider: str = Query(default="mt4")):
    try:
        if provider.lower() == "mt4":
            timeframe_map = {"1m":"M1", "5m":"M5", "15m":"M15", "30m":"M30",
                             "1h":"H1", "4h":"H4", "1d":"D1"}
            tf = timeframe_map.get(interval.lower())
            if not tf:
                raise HTTPException(400, "Unsupported timeframe.")
            bars = mt4_feed.get_candles(symbol, tf)
            return {"symbol": symbol.upper(), "interval": interval.lower(),
                    "provider": "mt4", "bars": bars[-limit:]}
        if provider.lower() == "biquote":
            return get_biquote_ohlc(symbol, interval, limit)
        raise HTTPException(400, "Unsupported market-data provider.")
    except mt4_feed.MT4FeedError as exc:
        raise HTTPException(503, str(exc))
    except MarketDataError as exc:
        raise HTTPException(502, str(exc))


@app.post("/api/v1/risk/position-size")
def position_size(payload: RiskPayload):
    return calculate_position_size(RiskRequest(**payload.model_dump()))


@app.post("/api/v1/analysis")
def analysis(payload: AnalysisPayload):
    symbol = payload.symbol.upper()
    account = {"balance": payload.balance, "risk_percent": payload.risk_percent} if payload.balance is not None else None
    contract = payload.contract.model_dump() if payload.contract is not None and payload.contract_verified else None
    try:
        if payload.provider.lower() == "mt4":
            quote = mt4_feed.get_quote(symbol)
            if contract is None:
                contract = mt4_feed.get_contract(symbol)
        elif payload.provider.lower() == "biquote":
            quote = get_biquote_tick(symbol)
        else:
            raise HTTPException(400, "Unsupported market-data provider.")
        if quote.get("stale") is not False:
            raise HTTPException(503, "Market quote is stale or freshness is unverified; signal blocked.")
        age = quote.get("quote_age_seconds")
        if isinstance(age, bool) or not isinstance(age, (int, float)) or age < 0 or age > 30:
            raise HTTPException(503, "Market quote age is missing or exceeds 30 seconds; signal blocked.")
        return analyze_market(symbol, payload.timeframe, payload.candles, account, contract, quote)
    except mt4_feed.MT4FeedError as exc:
        raise HTTPException(503, str(exc))
    except MarketDataError as exc:
        raise HTTPException(502, str(exc))
    except ValueError as exc:
        raise HTTPException(422, str(exc))
