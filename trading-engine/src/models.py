from dataclasses import dataclass
from typing import Literal

SignalSide = Literal["BUY", "SELL", "NO_TRADE"]

@dataclass
class OHLC:
    timestamp: int
    open: float
    high: float
    low: float
    close: float

@dataclass
class Signal:
    symbol: str
    side: SignalSide
    timeframe: str
    entry: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    reason: str = "No validated strategy is configured."
    expires_at: int | None = None
