# Event-Reaction Module

Measures how asset prices react to discrete, timestamped events (rate decisions,
tariffs, geopolitical shocks). Core principle: markets price the *surprise*, not
the event — every measurement is built on a surprise, never the raw event.

## Architecture (6 stages, ports-and-adapters)
- ingest/        adapters: prices, events, prediction-market odds (network ONLY here)
- align/         UTC event clock, log returns, event windows
- surprise/      surprise constructors (consensus, futures/Kuttner, odds, LLM)
- returns/       market-model abnormal returns + CAR
- jumps/         Lee-Mykland jump test
- cross_section/ CAR-on-exposure regression
The pure-stats stages (align, surprise, returns, jumps, cross_section) MUST NOT do I/O.

## Invariants (YOU MUST follow — these prevent silent, plausible-looking bugs)
- All timestamps are tz-aware UTC, to the minute. The event release timestamp is the join key.
- NEVER look ahead: the estimation window ends strictly before the event window (keep a buffer).
  A surprise may use ONLY data timestamped before the event.
- NEVER regress an outcome on the raw event; always on a surprise measure.
- For same-day/clustered events, returns are cross-correlated — do NOT trust the iid
  event-study t-test; use the cross-sectional (exposure) or portfolio route.
- Returns are log returns. CAR = sum of abnormal returns over the window.

## Data contracts
- events: DataFrame[event_id, ts_utc(UTC), kind, actual, consensus]
- prices: tz-aware UTC pd.Series, monotonic, gaps handled
- odds:   pd.Series in [0,1] indexed by UTC timestamp

## Testing (pytest)
- Deterministic synthetic fixtures, seeded RNG. Each stat stage has a recovery test:
  injected jump detected; known CAR recovered; known exposure coef recovered;
  standardized surprise has the right sign/scale.
- Property test: mutating post-event data must NOT change any surprise (no-look-ahead).
- Stats stages run fully offline; data adapters are mocked.

## Commands
- test: cd stock_microservices/event-reaction-lib && pytest tests/
