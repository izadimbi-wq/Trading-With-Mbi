# Implementation Plan

## Phase 1 — foundation
- Compile Android shell and backend.
- Confirm exact Alpari MT4 account type and symbol specifications.
- Add authenticated feed transport and server-side storage.
- Add candle aggregation and chart rendering.

## Phase 2 — analysis
- Implement and unit-test indicators.
- Add multi-timeframe strategy rules and NO_TRADE reasons.
- Backtest with realistic spread, commission and slippage.

## Phase 3 — demo integration
- Add command signing, unique IDs, expiry and execution acknowledgements.
- Keep EA order execution disabled until demo tests pass.
- Test disconnects, duplicate commands, stale prices and margin constraints.

## Phase 4 — controlled release
- Security review, monitoring, audit logs and recovery procedures.
- Enable live execution only after explicit opt-in and independent validation.
