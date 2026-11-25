
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from risk_management.sizing import (
    calculate_position_size,
    RiskRequest
)

from market_data.biquote_client import (
    get_tick,
    get_ohlc,
    MarketDataError
)

app = FastAPI(
    title="TradingAI API",
    version="0.2.0"
)

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


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "TradingAI API",
        "mode": "market-data-enabled"
    }


@app.get("/api/v1/market/snapshot")
def market_snapshot():

    results = {}

    for symbol in SUPPORTED_SYMBOLS:
        try:
            results[symbol] = {
                "status": "ok",
                "data": get_tick(symbol)
            }

        except MarketDataError as exc:
            results[symbol] = {
                "status": "unavailable",
                "message": str(exc)
            }

    available = sum(
        1 for item in results.values()
        if item["status"] == "ok"
    )

    return {
        "provider": "biquote",
        "status": (
            "ok" if available == len(SUPPORTED_SYMBOLS)
            else "partial" if available > 0
            else "unavailable"
        ),
        "symbols": results
    }


@app.get("/api/v1/market/{symbol}/tick")
def market_tick(symbol: str):

    symbol = symbol.upper()

    if symbol not in SUPPORTED_SYMBOLS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported symbol."
        )

    try:
        return get_tick(symbol)

    except MarketDataError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc)
        )


@app.get("/api/v1/market/{symbol}/ohlc")
def market_ohlc(
    symbol: str,
    interval: str = Query(default="5m"),
    limit: int = Query(default=100, ge=1, le=1000)
):

    symbol = symbol.upper()

    if symbol not in SUPPORTED_SYMBOLS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported symbol."
        )

    try:
        return get_ohlc(
            symbol=symbol,
            interval=interval,
            limit=limit
        )

    except MarketDataError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc)
        )


@app.post("/api/v1/risk/position-size")
def position_size(payload: RiskPayload):

    result = calculate_position_size(
        RiskRequest(**payload.model_dump())
    )

    return result
