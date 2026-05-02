# Architecture

```
                     ┌────────────────────────────────────────────────┐
                     │  agent.run_forever() / agent.tick()            │
                     │                                                │
   ┌────────────┐    │  1) for each halal pair: fetch_ohlcv()         │
   │  Exchange  │◀───┤  2) build TechnicalSnapshot                    │
   │  (CCXT)    │    │  3) ResearchAgent.evaluate(snap) → Thesis      │
   └────────────┘    │  4) RiskManager.size_buy() / should_exit()     │
                     │  5) Executor.buy() / sell()                    │
                     │  6) Ledger.record_trade(), record_equity()     │
                     └────────────────────────────────────────────────┘
                                         │
                          ┌──────────────┼──────────────┐
                          ▼              ▼              ▼
                    PaperExecutor  LiveExecutor   Ledger (SQLite)
                    (in-memory)    (CCXT spot)    (data/agent.db)
```

## Module map

| Module | Responsibility |
|--------|----------------|
| `config.py` | Load settings via pydantic-settings (env / .env). |
| `halal.py` | Hard-coded Sharia whitelist + `assert_halal_pair`. |
| `safety.py` | `enable_live.md` ack-file gate for live mode. |
| `exchange.py` | CCXT spot wrapper; halal-pair check on every order. |
| `market_data.py` | OHLCV → indicators (RSI, EMA, MACD). |
| `research.py` | Rule-based or LLM research → Thesis (BUY/HOLD/SELL). |
| `risk.py` | Position sizing, max-positions, daily-loss circuit breaker. |
| `executor.py` | `PaperExecutor` (default) and `LiveExecutor`. |
| `ledger.py` | aiosqlite persistence: trades, positions, equity snapshots. |
| `agent.py` | Glue: per-tick loop and `build_agent()` factory. |
| `dashboard.py` | FastAPI `/healthz` and `/state`. |
| `__main__.py` | CLI entry — `python -m halal_agent` (or `--once`). |

## Safety properties

These are enforced in code and impossible to bypass via configuration:

1. **Halal whitelist** — any order on a non-whitelisted pair raises
   `HalalViolation` *before* hitting the exchange.
2. **Spot only** — `defaultType: 'spot'` set on the CCXT client; no margin
   or futures methods are exposed.
3. **Live-mode gate** — `TRADING_MODE=live` requires a committed
   `enable_live.md` file with the exact phrase
   `I_HAVE_READ_THE_RISKS_AND_AUTHORIZE_LIVE_TRADING`.
4. **Daily-loss circuit breaker** — when `(equity_today_open - equity) /
   equity_today_open >= MAX_DAILY_LOSS_PCT`, all new trades are refused
   and the loop sleeps 1 hour before retry.
5. **Position sizing cap** — every buy is capped at
   `MAX_POSITION_PCT * equity`; floor at `MIN_TRADE_QUOTE`.

## Decision flow per pair

```
fetch OHLCV  →  TechnicalSnapshot
                       │
                       ▼
holding this pair?  ─yes─► should_exit(stop_loss / take_profit)?
                       │                            │
                       no                          yes ─► sell()
                       ▼
        researcher.evaluate(snap) → Thesis
                       │
                       ▼
              action == BUY?  ─no──► skip
                       │
                       yes
                       ▼
        risk.size_buy(state, price, confidence)
                       │
                       ▼
              executor.buy(pair, quote_amount, price)
```

The LLM never decides position size — it only contributes to the
directional thesis. Risk control stays deterministic.
