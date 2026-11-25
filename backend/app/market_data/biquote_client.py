
import json
import math
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://biquote.io/api"

ALLOWED_SYMBOLS = {"XAUUSD", "EURUSD", "XAGUSD"}

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
            "User-Agent": "Trading-With-Mbi/0.2"
        }
    )

    try:
        with urlopen(request, timeout=10) as response:
            result = json.loads(
                response.read().decode("utf-8")
            )

        if not isinstance(result, dict):
            raise MarketDataError(
                "Invalid market data response format."
            )

        return result

    except MarketDataError:
        raise

    except (HTTPError, URLError, TimeoutError) as exc:
        raise MarketDataError(
            f"Market data request failed: {exc}"
        ) from exc

    except (ValueError, UnicodeDecodeError) as exc:
        raise MarketDataError(
            "Invalid market data response."
        ) from exc


def _valid_number(value) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value > 0
    )


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
        if not _valid_number(data[key]):
            raise MarketDataError(
                f"Invalid {key} price."
            )

    bid = data["bid"]
    ask = data["ask"]
    mid = data["mid"]

    if ask < bid or not bid <= mid <= ask:
        raise MarketDataError(
            "Invalid bid/ask/mid relationship."
        )

    return {
        "symbol": symbol,
        "bid": bid,
        "ask": ask,
        "mid": mid,
        "spread": ask - bid,
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

    if (
        isinstance(limit, bool)
        or not isinstance(limit, int)
        or not 1 <= limit <= 1000
    ):
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

    validated_bars = []

    for bar in bars:
        if not isinstance(bar, dict):
            raise MarketDataError("Invalid candle format.")

        required = ("open", "high", "low", "close")

        if not all(key in bar for key in required):
            raise MarketDataError("Incomplete candle data.")

        for key in required:
            if not _valid_number(bar[key]):
                raise MarketDataError(
                    f"Invalid candle {key} value."
                )

        open_price = bar["open"]
        high_price = bar["high"]
        low_price = bar["low"]
        close_price = bar["close"]

        if (
            high_price < max(open_price, close_price)
            or low_price > min(open_price, close_price)
            or high_price < low_price
        ):
            raise MarketDataError(
                "Inconsistent OHLC candle."
            )

        validated_bars.append(bar)

    return {
        "symbol": symbol,
        "interval": interval,
        "provider": "biquote",
        "bars": validated_bars,
        "received_at": datetime.now(
            timezone.utc
        ).isoformat()
    }
