import json
import math
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://biquote.io/api"
ALLOWED_INTERVALS = {"1m", "5m", "15m", "30m", "1h", "4h", "1d"}
CURRENCY_CODES = {
    "USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD",
    "CNH", "CNY", "HKD", "SGD", "SEK", "NOK", "DKK", "PLN",
    "CZK", "HUF", "TRY", "ZAR", "MXN", "ILS", "THB", "AED",
}
METALS = {"XAU", "XAG", "XPT", "XPD"}


class MarketDataError(Exception):
    pass


def normalize_symbol(symbol: str) -> str:
    raw = "".join(ch for ch in str(symbol).upper() if ch.isalpha())
    allowed = CURRENCY_CODES | METALS
    for i in range(max(1, len(raw) - 5)):
        candidate = raw[i:i + 6]
        if len(candidate) == 6 and candidate[:3] in allowed and candidate[3:] in allowed:
            return candidate
    return raw


def is_supported_symbol(symbol: str) -> bool:
    s = normalize_symbol(symbol)
    if len(s) != 6:
        return False
    a, b = s[:3], s[3:]
    return (a in CURRENCY_CODES and b in CURRENCY_CODES and a != b) or (
        a in METALS and b in {"USD", "EUR", "GBP", "JPY", "CHF"}
    )


def _get_json(url: str) -> dict:
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "Trading-With-Mbi/0.5"})
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
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0


def _valid_price(symbol: str, value) -> bool:
    if not _valid_number(value):
        return False
    # Generic scale checks only. Contract-specific tick size/digits are supplied by MT4.
    return 0.000001 <= float(value) <= 1_000_000


def _validate_ohlc_price(symbol: str, bar: dict) -> None:
    for key in ("open", "high", "low", "close"):
        if not _valid_price(symbol, bar.get(key)):
            raise MarketDataError(f"Invalid candle {key} value for {symbol}.")
    o, h, l, c = (float(bar[k]) for k in ("open", "high", "low", "close"))
    if h < max(o, c) or l > min(o, c) or h < l:
        raise MarketDataError("Inconsistent OHLC candle.")


def get_tick(symbol: str) -> dict:
    symbol = normalize_symbol(symbol)
    if not is_supported_symbol(symbol):
        raise MarketDataError("Unsupported symbol.")
    data = _get_json(f"{BASE_URL}/{symbol}?allowStale=false")
    required = ("bid", "ask", "mid", "timestamp")
    if not all(k in data for k in required):
        raise MarketDataError("Incomplete tick data.")
    if not isinstance(data["timestamp"], str) or not data["timestamp"].strip():
        raise MarketDataError("Invalid tick timestamp.")
    for key in ("bid", "ask", "mid"):
        if not _valid_price(symbol, data[key]):
            raise MarketDataError(f"Invalid {key} price for {symbol}.")
    bid, ask, mid = float(data["bid"]), float(data["ask"]), float(data["mid"])
    if ask < bid or not bid <= mid <= ask:
        raise MarketDataError("Invalid bid/ask/mid relationship.")
    return {
        "symbol": symbol, "bid": bid, "ask": ask, "mid": mid,
        "spread": ask - bid, "timestamp": data["timestamp"],
        "source": data.get("source"), "provider": "biquote",
        "market_state": data.get("marketState"), "stale": data.get("stale", True),
        "quote_age_seconds": data.get("quoteAgeSeconds"),
        "received_at": datetime.now(timezone.utc).isoformat()
    }


def get_ohlc(symbol: str, interval: str = "5m", limit: int = 100) -> dict:
    symbol = normalize_symbol(symbol)
    if not is_supported_symbol(symbol):
        raise MarketDataError("Unsupported symbol.")
    if interval not in ALLOWED_INTERVALS:
        raise MarketDataError("Unsupported timeframe.")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 1000:
        raise MarketDataError("Invalid candle limit.")
    params = urlencode({"interval": interval, "limit": limit})
    data = _get_json(f"{BASE_URL}/{symbol}/ohlc?{params}")
    bars = data.get("bars")
    if not isinstance(bars, list):
        raise MarketDataError("Invalid candle response.")
    checked = []
    for bar in bars:
        if not isinstance(bar, dict):
            raise MarketDataError("Invalid candle format.")
        _validate_ohlc_price(symbol, bar)
        checked.append(bar)
    return {"symbol": symbol, "interval": interval, "provider": "biquote",
            "bars": checked, "received_at": datetime.now(timezone.utc).isoformat()}
