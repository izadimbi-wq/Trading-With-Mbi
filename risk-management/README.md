# Risk Management

The backend's `app/risk_management/sizing.py` is the initial implementation.
It calculates size from broker-provided tick size and tick value per lot, rounds down to lot step,
and rejects when the minimum lot breaches the risk budget.

Do not use generic pip-value assumptions for XAUUSD. Obtain actual symbol properties from MT4.
