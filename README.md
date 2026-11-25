# TradingAI — Initial Starter Package

A modular starter scaffold for an Android trading assistant focused on XAUUSD and EURUSD.
This is an **analysis-first / demo-first** foundation, not a production trading system.

## Modules
- `android-app/`: Kotlin + Jetpack Compose starter UI
- `backend/`: FastAPI service exposing health, market snapshot placeholder, and risk validation
- `trading-engine/`: indicator and signal-domain placeholders
- `risk-management/`: position sizing with strict minimum-lot rejection
- `mt4-expert-advisor/`: MT4 EA bridge skeleton; trading disabled by default
- `tests/`: risk-management unit tests
- `documentation/`: architecture, setup, and safety notes

## Important account defaults
- Reference balance: USD 50
- Default risk: 0.5% (USD 0.25)
- Hard per-trade risk ceiling: 1% (USD 0.50)
- Minimum lot: 0.01 (must be confirmed against the actual Alpari account/symbol)
- Target minimum reward/risk: 2.0
- One open trade maximum
- No trade without a stop loss
- If minimum lot exceeds the risk budget, return `REJECT`; never round volume upward.

These are configurable reference values, not confirmation of current broker contract specifications.
The live MT4 symbol specification (tick size/value, contract size, lot step, spread, commission)
must be read and validated before any real order.

## Quick start — backend
```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Open `http://127.0.0.1:8000/docs`.

## Android
Open `android-app/` in Android Studio (recent stable version). The Android module is a minimal
Compose shell; connect it to a secured backend before displaying live prices.

## MT4
Copy `mt4-expert-advisor/TradingAI_Bridge.mq4` into `MQL4/Experts/`, compile in MetaEditor,
and attach to a **demo** chart first. It sends a basic heartbeat only when configured.
Order execution is disabled by default. Do not enable live trading until authentication,
TLS transport, replay protection, broker-spec validation, demo forward testing, and explicit
user confirmation are implemented and audited.

## Security
Never commit MT4 passwords, API keys, access tokens, account numbers, or private server URLs.
Use environment variables / a secrets manager. Do not expose the backend directly to the internet.
