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

# Deliberately broad safety bands. They are not trading levels; they only
# reject obviously mis-scaled or wrong-symbol prices (for example XAUUSD=1.10).
SYMBOL_PRICE_RANGES = {
    "XAUUSD": (100.0, 100000.0),
    "EURUSD": (0.1, 10.0),
    "XAGUSD": (1.0, 1000.0),
}


class MarketDataError(Exception):
    pass


def _get_json(url: str) -> dict:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "Trading-With-Mbi/0.3"
        }
    )

    try:
        with urlopen(request, timeout=10) as response:
            result = json.loads(response.read().decode("utf-8"))

        if not isinstance(result, dict):
            raise MarketDataError("Invalid market data response format.")
        return result

    except MarketDataError:
        raise
    except (HTTPError, URLError, TimeoutError) as exc:
        raise MarketDataError(f"Market data request failed: {exc}") from exc
    except (ValueError, UnicodeDecodeError) as exc:
        raise MarketDataError("Invalid market data response.") from exc


def _valid_number(value) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value > 0
    )


def _valid_symbol_price(symbol: str, value) -> bool:
    if not _valid_number(value):
        return False
    low, high = SYMBOL_PRICE_RANGES[symbol]
    return low <= float(value) <= high


def _validate_ohlc_price(symbol: str, bar: dict) -> None:
    for key in ("open", "high", "low", "close"):
        if not _valid_symbol_price(symbol, bar.get(key)):
            raise MarketDataError(
                f"Invalid candle {key} value for {symbol}."
            )

    open_price = float(bar["open"])
    high_price = float(bar["high"])
    low_price = float(bar["low"])
    close_price = float(bar["close"])

    if (
        high_price < max(open_price, close_price)
        or low_price > min(open_price, close_price)
        or high_price < low_price
    ):
        raise MarketDataError("Inconsistent OHLC candle.")


def get_tick(symbol: str) -> dict:
    symbol = symbol.upper()

    if symbol not in ALLOWED_SYMBOLS:
        raise MarketDataError("Unsupported symbol.")

    data = _get_json(f"{BASE_URL}/{symbol}?allowStale=false")
    required = ("bid", "ask", "mid", "timestamp")

    if not all(key in data for key in required):
        raise MarketDataError("Incomplete tick data.")

    if not isinstance(data["timestamp"], str) or not data["timestamp"].strip():
        raise MarketDataError("Invalid tick timestamp.")

    for key in ("bid", "ask", "mid"):
        if not _valid_symbol_price(symbol, data[key]):
            raise MarketDataError(
                f"Invalid {key} price for {symbol}; quote rejected."
            )

    bid = float(data["bid"])
    ask = float(data["ask"])
    mid = float(data["mid"])

    if ask < bid or not bid <= mid <= ask:
        raise MarketDataError("Invalid bid/ask/mid relationship.")

    # Always derive spread from the validated bid/ask pair. Do not trust a
    # separately rounded provider spread field.
    spread = ask - bid

    return {
        "symbol": symbol,
        "bid": bid,
        "ask": ask,
        "mid": mid,
        "spread": spread,
        "timestamp": data["timestamp"],
        "source": data.get("source"),
        "provider": "biquote",
        "market_state": data.get("marketState"),
        "stale": data.get("stale", True),
        "quote_age_seconds": data.get("quoteAgeSeconds"),
        "received_at": datetime.now(timezone.utc).isoformat()
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

    params = urlencode({"interval": interval, "limit": limit})
    data = _get_json(f"{BASE_URL}/{symbol}/ohlc?{params}")
    bars = data.get("bars")

    if not isinstance(bars, list):
        raise MarketDataError("Invalid candle response.")

    validated_bars = []
    for bar in bars:
        if not isinstance(bar, dict):
            raise MarketDataError("Invalid candle format.")
        _validate_ohlc_price(symbol, bar)
        validated_bars.append(bar)

    return {
        "symbol": symbol,
        "interval": interval,
        "provider": "biquote",
        "bars": validated_bars,
        "received_at": datetime.now(timezone.utc).isoformat()
    }
