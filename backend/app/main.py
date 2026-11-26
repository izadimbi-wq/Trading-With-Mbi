from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from risk_management.sizing import calculate_position_size, RiskRequest
from technical_analysis.strategy import analyze_market
from market_data.biquote_client import get_tick, get_ohlc, MarketDataError

app = FastAPI(title="TradingAI API", version="0.3.2")
SUPPORTED_SYMBOLS = ["XAUUSD", "EURUSD", "XAGUSD"]


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
    balance: float | None = Field(default=50.0, gt=0)
    risk_percent: float = Field(default=1.0, gt=0, le=1)
    contract: ContractPayload | None = None
    # Contract values from the mobile app are ignored unless explicitly verified
    # against the user's live MT4 symbol Specification.
    contract_verified: bool = False


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "TradingAI API",
        "mode": "analysis-and-market-data",
    }


@app.get("/api/v1/market/snapshot")
def market_snapshot():
    results = {}
    for symbol in SUPPORTED_SYMBOLS:
        try:
            results[symbol] = {"status": "ok", "data": get_tick(symbol)}
        except MarketDataError as exc:
            results[symbol] = {"status": "unavailable", "message": str(exc)}
    available = sum(1 for item in results.values() if item["status"] == "ok")
    status = (
        "ok" if available == len(SUPPORTED_SYMBOLS)
        else "partial" if available
        else "unavailable"
    )
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

    # Ignore provisional app-side contract constants unless the user explicitly
    # verifies them against the live MT4 Specification.
    contract = (
        payload.contract.model_dump()
        if payload.contract is not None and payload.contract_verified
        else None
    )

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
            "risk_budget_usd": round(
                payload.balance * payload.risk_percent / 100, 2
            ) if payload.balance is not None else None,
        }

        if symbol == "XAUUSD":
            if contract is None:
                result["contract_profile"] = {
                    "status": "UNVERIFIED",
                    "broker": "Alpari Standard MT4",
                    "required_fields": [
                        "tick_size",
                        "tick_value_per_lot",
                        "min_lot",
                        "lot_step",
                        "max_lot",
                    ],
                    "message": (
                        "Position sizing is disabled until live MT4 contract "
                        "specifications are verified."
                    ),
                }
            else:
                result["contract_profile"] = {
                    **contract,
                    "status": "VERIFIED_BY_USER",
                    "source": "User-confirmed live MT4 Specification",
                }
        return result
    except ValueError as exc:
        raise HTTPException(422, str(exc))
