"""Authenticated in-memory market-data bridge populated by the MT4 Expert Advisor.

Set TRADINGAI_MT4_TOKEN in the backend environment to a long random secret.
The bridge intentionally stores only market data; it never places orders.
"""
import os
import re
import secrets
import threading
import time
from datetime import datetime, timezone
from typing import Any

MT4_TOKEN = os.getenv("TRADINGAI_MT4_TOKEN", "").strip()
MAX_AGE_SECONDS = int(os.getenv("TRADINGAI_MT4_MAX_AGE_SECONDS", "30"))
_lock = threading.RLock()
_quotes: dict[str, dict[str, Any]] = {}
_candles: dict[tuple[str, str], list[dict[str, Any]]] = {}
_contracts: dict[str, dict[str, Any]] = {}
_last_update: dict[str, float] = {}

_CURRENCY_CODES = {
    "USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD",
    "CNH", "CNY", "HKD", "SGD", "SEK", "NOK", "DKK", "PLN",
    "CZK", "HUF", "TRY", "ZAR", "MXN", "ILS", "THB", "AED",
}
_METALS = {"XAU", "XAG", "XPT", "XPD"}


class MT4FeedError(ValueError):
    pass


def normalize_symbol(symbol: str) -> str:
    """Strip common broker affixes while preserving the broker's raw symbol separately."""
    raw = re.sub(r"[^A-Z]", "", str(symbol).upper())
    # Search for a known 6-character FX pair or a supported metal pair in a broker symbol.
    for i in range(max(0, len(raw) - 5)):
        candidate = raw[i:i + 6]
        if len(candidate) == 6 and candidate[:3] in _CURRENCY_CODES | _METALS and candidate[3:] in _CURRENCY_CODES | {"USD"}:
            return candidate
    return raw


def is_supported_market_symbol(symbol: str) -> bool:
    s = normalize_symbol(symbol)
    if len(s) != 6:
        return False
    base, quote = s[:3], s[3:]
    return (
        (base in _CURRENCY_CODES and quote in _CURRENCY_CODES and base != quote)
        or (base in _METALS and quote in {"USD", "EUR", "GBP", "JPY", "CHF"})
    )


def _auth(token: str | None) -> None:
    if not MT4_TOKEN:
        raise MT4FeedError("MT4 bridge is disabled: TRADINGAI_MT4_TOKEN is not configured.")
    if not token or not secrets.compare_digest(token, MT4_TOKEN):
        raise PermissionError("Invalid MT4 bridge token.")


def ingest(payload: dict, token: str | None) -> dict:
    _auth(token)
    if not isinstance(payload, dict):
        raise MT4FeedError("Payload must be an object.")
    raw_symbol = str(payload.get("symbol", "")).upper().strip()
    symbol = normalize_symbol(raw_symbol)
    if not raw_symbol or not is_supported_market_symbol(raw_symbol):
        raise MT4FeedError("Unsupported or unrecognized market symbol.")
    bid, ask = payload.get("bid"), payload.get("ask")
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in (bid, ask)):
        raise MT4FeedError("Bid and ask must be numeric.")
    if bid <= 0 or ask < bid:
        raise MT4FeedError("Invalid Bid/Ask values.")
    now = time.time()
    quote = {
        "symbol": symbol, "broker_symbol": raw_symbol,
        "bid": float(bid), "ask": float(ask), "mid": (float(bid) + float(ask)) / 2,
        "spread": float(ask) - float(bid),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "MT4-Alpari", "provider": "mt4",
        "stale": False, "quote_age_seconds": 0,
        "received_at": datetime.now(timezone.utc).isoformat(),
    }
    candles = payload.get("candles", [])
    if not isinstance(candles, list) or len(candles) > 500:
        raise MT4FeedError("Candles must be a list of at most 500 items.")
    checked = []
    for bar in candles:
        if not isinstance(bar, dict):
            raise MT4FeedError("Invalid candle item.")
        vals = [bar.get(k) for k in ("open", "high", "low", "close")]
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or v <= 0 for v in vals):
            raise MT4FeedError("Invalid OHLC values.")
        o, h, l, c = map(float, vals)
        if h < max(o, c) or l > min(o, c) or h < l:
            raise MT4FeedError("Inconsistent OHLC candle.")
        checked.append({
            "time": bar.get("time"),
            "open": o, "high": h, "low": l, "close": c,
            "tick_volume": int(bar.get("tick_volume", 0)),
            "isOpen": bool(bar.get("isOpen", False)),
        })
    contract = payload.get("contract")
    if contract is not None:
        if not isinstance(contract, dict):
            raise MT4FeedError("Invalid contract specification.")
        keys = ("tick_size", "tick_value_per_lot", "min_lot", "lot_step", "max_lot")
        if any(isinstance(contract.get(k), bool) or not isinstance(contract.get(k), (int, float)) or contract[k] <= 0 for k in keys):
            raise MT4FeedError("Incomplete or invalid contract specification.")
        _contracts[symbol] = {k: float(contract[k]) for k in keys}
    with _lock:
        _quotes[symbol] = quote
        _candles[(symbol, str(payload.get("timeframe", "M5")).upper())] = checked
        _last_update[symbol] = now
    return {"accepted": True, "symbol": symbol, "broker_symbol": raw_symbol, "candles_received": len(checked)}


def list_symbols() -> list[dict]:
    now = time.time()
    with _lock:
        return [
            {"symbol": s, "broker_symbol": q["broker_symbol"],
             "status": "ok" if now - _last_update.get(s, 0) <= MAX_AGE_SECONDS else "stale",
             "quote_age_seconds": round(now - _last_update.get(s, 0), 2)}
            for s, q in sorted(_quotes.items())
        ]


def get_quote(symbol: str) -> dict:
    s = normalize_symbol(symbol)
    with _lock:
        q = _quotes.get(s)
        updated = _last_update.get(s)
        if q is None or updated is None:
            raise MT4FeedError("No MT4 quote received for this symbol.")
        result = dict(q)
        age = max(0.0, time.time() - updated)
        result["quote_age_seconds"] = age
        result["stale"] = age > MAX_AGE_SECONDS
        return result


def get_candles(symbol: str, timeframe: str = "M5") -> list[dict]:
    s = normalize_symbol(symbol)
    with _lock:
        bars = _candles.get((s, timeframe.upper()))
        if bars is None:
            raise MT4FeedError("No MT4 candles received for this symbol/timeframe.")
        return list(bars)


def get_contract(symbol: str) -> dict | None:
    with _lock:
        item = _contracts.get(normalize_symbol(symbol))
        return dict(item) if item else None
