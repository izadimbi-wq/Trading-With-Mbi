from fastapi import FastAPI
from pydantic import BaseModel, Field
from risk_management.sizing import calculate_position_size, RiskRequest

app = FastAPI(title="TradingAI API", version="0.1.0")

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
    return {"status": "ok", "service": "TradingAI API", "mode": "starter"}

@app.get("/api/v1/market/snapshot")
def market_snapshot():
    # Deliberately no fabricated/live prices. Integrate an authenticated MT4 feed.
    return {
        "status": "unavailable",
        "message": "No live market-data provider is configured.",
        "symbols": ["XAUUSD", "EURUSD"]
    }

@app.post("/api/v1/risk/position-size")
def position_size(payload: RiskPayload):
    result = calculate_position_size(RiskRequest(**payload.model_dump()))
    return result
