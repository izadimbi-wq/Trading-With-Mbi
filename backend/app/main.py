from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from risk_management.sizing import calculate_position_size, RiskRequest
from risk_management.trade_plan import TradePlanRequest, create_trade_plan
from technical_analysis.strategy import analyze_market
from market_data.biquote_client import get_tick, get_ohlc, MarketDataError

app = FastAPI(title="TradingAI API", version="0.3.1")
SUPPORTED_SYMBOLS = ["XAUUSD", "EURUSD", "XAGUSD"]

# User-confirmed account profile. The contract assumptions below are used only
# for XAUUSD and must be checked against the live MT4 Specification before trading.
DEFAULT_XAUUSD_CONTRACT = {
    "tick_size": 0.01,
    "tick_value_per_lot": 1.0,  # 100 oz/lot * $0.01 tick = $1 per tick per 1.00 lot
    "min_lot": 0.01,
    "lot_step": 0.01,
    "max_lot": 100.0,  # software ceiling, not a claim about broker's maximum
}


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
    # User confirmed USD account balance $50 and max risk 1% per trade.
    balance: float | None = Field(default=50.0, gt=0)
    risk_percent: float = Field(default=1.0, gt=0, le=1)
    contract: ContractPayload | None = None


@app.get("/health")
def health():
    return {"status": "ok", "service": "TradingAI API", "mode": "analysis-and-market-data"}


@app.get("/api/v1/market/snapshot")
def market_snapshot():
    results = {}
    for symbol in SUPPORTED_SYMBOLS:
        try:
            results[symbol] = {"status": "ok", "data": get_tick(symbol)}
        except MarketDataError as exc:
            results[symbol] = {"status": "unavailable", "message": str(exc)}
    available = sum(1 for item in results.values() if item["status"] == "ok")
    status = "ok" if available == len(SUPPORTED_SYMBOLS) else "partial" if available else "unavailable"
    return {"provider": "biquote", "status": status, "symbols": results}


@app.get("/api/v1/market/{symbol}/tick")
def market_tick(symbol: str):
    symbol = symbol.upper()
    if symbol not in SUPPORTED_SYMBOLS:
        raise HTTPException(400, "Unsupported symbol.")
    try:
        return get_tick(symbol)
    except MarketDataError as exc:
        raise HTTPException(502, str(exc))


@app.get("/api/v1/market/{symbol}/ohlc")
def market_ohlc(
    symbol: str,
    interval: str = Query(default="5m"),
    limit: int = Query(default=100, ge=1, le=1000),
):
    symbol = symbol.upper()
    if symbol not in SUPPORTED_SYMBOLS:
        raise HTTPException(400, "Unsupported symbol.")
    try:
        return get_ohlc(symbol, interval, limit)
    except MarketDataError as exc:
        raise HTTPException(502, str(exc))


@app.post("/api/v1/risk/position-size")
def position_size(payload: RiskPayload):
    return calculate_position_size(RiskRequest(**payload.model_dump()))


@app.post("/api/v1/analysis")
def analysis(payload: AnalysisPayload):
    symbol = payload.symbol.upper()
    if symbol not in SUPPORTED_SYMBOLS:
        raise HTTPException(400, "Unsupported symbol.")

    account = {
        "balance": payload.balance,
        "risk_percent": payload.risk_percent,
    } if payload.balance is not None else None

    # Never apply XAUUSD contract assumptions to EURUSD or XAGUSD.
    if symbol == "XAUUSD":
        contract = (
            payload.contract.model_dump()
            if payload.contract is not None
            else DEFAULT_XAUUSD_CONTRACT.copy()
        )
    else:
        contract = payload.contract.model_dump() if payload.contract is not None else None

    try:
        result = analyze_market(
            symbol,
            payload.timeframe,
            payload.candles,
            account,
            contract,
        )
        result["account_risk_profile"] = {
            "balance_usd": payload.balance,
            "risk_percent": payload.risk_percent,
            "risk_budget_usd": round(payload.balance * payload.risk_percent / 100, 2)
            if payload.balance is not None else None,
        }
        if symbol == "XAUUSD":
            result["contract_profile"] = {
                **contract,
                "source": "provisional calculation from user-provided MT4 contract size and tick size",
                "must_verify_in_mt4": True,
            }
        return result
    except ValueError as exc:
        raise HTTPException(422, str(exc))
