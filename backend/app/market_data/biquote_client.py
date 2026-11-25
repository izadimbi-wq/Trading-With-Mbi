
import json
import math
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://biquote.io/api"

ALLOWED_SYMBOLS = {
    "XAUUSD",
    "EURUSD",
    "XAGUSD",
}

ALLOWED_INTERVALS = {
    "1m", "5m", "15m", "30m",
    "1h", "4h", "1d",
}


class MarketDataError(Exception):
    pass


def _get_json(url: str) -> dict:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "Trading-With-Mbi/0.1"
        }
    )

    try:
        with urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))

    except (HTTPError, URLError, TimeoutError) as exc:
        raise MarketDataError(
            f"Market data request failed: {exc}"
        ) from exc

    except (ValueError, UnicodeDecodeError) as exc:
        raise MarketDataError(
            "Invalid market data response."
        ) from exc


def get_tick(symbol: str) -> dict:
    symbol = symbol.upper()

    if symbol not in ALLOWED_SYMBOLS:
        raise MarketDataError("Unsupported symbol.")

    data = _get_json(
        f"{BASE_URL}/{symbol}?allowStale=false"
    )

    required = ("bid", "ask", "mid", "timestamp")

    if not all(key in data for key in required):
        raise MarketDataError("Incomplete tick data.")

    for key in ("bid", "ask", "mid"):
        value = data[key]

        if not isinstance(value, (int, float)):
            raise MarketDataError("Invalid price value.")

        if not math.isfinite(value) or value <= 0:
            raise MarketDataError("Invalid price value.")

    if data["ask"] < data["bid"]:
        raise MarketDataError("Invalid bid/ask relationship.")

    return {
        "symbol": symbol,
        "bid": data["bid"],
        "ask": data["ask"],
        "mid": data["mid"],
        "spread": data["ask"] - data["bid"],
        "timestamp": data["timestamp"],
        "source": data.get("source"),
        "provider": "biquote",
        "market_state": data.get("marketState"),
        "stale": data.get("stale", True),
        "quote_age_seconds": data.get("quoteAgeSeconds"),
        "received_at": datetime.now(
            timezone.utc
        ).isoformat()
    }


def get_ohlc(
    symbol: str,
    interval: str = "5m",
    limit: int = 100
) -> dict:

    symbol = symbol.upper()

    if symbol not in ALLOWED_SYMBOLS:
        raise MarketDataError("Unsupported symbol.")

    if interval not in ALLOWED_INTERVALS:
        raise MarketDataError("Unsupported timeframe.")

    if not 1 <= limit <= 1000:
        raise MarketDataError("Invalid candle limit.")

    params = urlencode({
        "interval": interval,
        "limit": limit
    })

    data = _get_json(
        f"{BASE_URL}/{symbol}/ohlc?{params}"
    )

    bars = data.get("bars")

    if not isinstance(bars, list):
        raise MarketDataError("Invalid candle response.")

    return {
        "symbol": symbol,
        "interval": interval,
        "provider": "biquote",
        "bars": bars,
        "received_at": datetime.now(
            timezone.utc
        ).isoformat()
    }

