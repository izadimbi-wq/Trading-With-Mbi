# Architecture

```text
Alpari MT4 (EA) -> secured market-data bridge -> Backend API
                                      |             |
                                      |             +-> Trading Engine
                                      |             +-> Risk Management
                                      |             +-> Signal/history store
                                      v
                              Android Compose App
```

The backend must be the authority for signal expiry, symbol metadata, risk checks and command IDs.
The app is a client, not a trusted execution authority. Any future order request must require
explicit user confirmation and a fresh server-side risk validation.
