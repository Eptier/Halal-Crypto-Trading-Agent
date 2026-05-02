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
| `market_data.py` | OHLCV → indicators (RSI, EMA stack, MACD + histogram, Bollinger Bands, ATR, volume z-score) and candle pattern flags (engulfing, hammer, shooting star, doji). |
| `research.py` | Rule-based **confluence-scoring** agent or LLM research → Thesis (BUY/HOLD/SELL + confidence). |
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
        researcher.evaluate(snap) → Thesis (BUY/HOLD/SELL + confidence)
                       │
        ┌──────────────┴──────────────┐
        │ holding?                    │ not holding
        ▼                             ▼
SELL with confidence ≥ 0.4 ?     action == BUY ?
        │   yes ─► sell()             │  yes
        │   no                        ▼
        ▼                       risk.size_buy(state, price, confidence)
% stop-loss / take-profit ?           │
        │   yes ─► sell()             ▼
        │   no  ─► hold         executor.buy(pair, quote_amount, price)
```

### Smart exit (multi-indicator first, % as safety net)

The agent prefers **research-driven exits** — when the rule-based
confluence agent (or the LLM) emits a confident `SELL` thesis, the agent
exits immediately. The fixed-percentage stop-loss / take-profit only
fires as a **safety net** when the indicators are inconclusive but price
has moved decisively past the configured thresholds. This matches the
intuitive "use the indicators to decide when to sell, fall back to %
when the picture is unclear" behaviour.

### Confluence scoring (rule-based)

The default research agent assigns weights to independent signals and
sums them into buy / sell scores:

| Signal | BUY weight | SELL weight |
|--------|-----------:|------------:|
| RSI oversold (<30) / overbought (>70) | +2 | +2 |
| RSI lower-half (<45) / elevated (>60) | +1 | +1 |
| Near lower / upper Bollinger Band | +2 | +2 |
| EMA stack 9>21>50 / 9<21<50 | +2 | +2 |
| EMA21 vs EMA50 only | +1 | +1 |
| MACD bullish / bearish cross | +2 | +2 |
| MACD histogram positive / negative | +1 | +1 |
| Bullish / bearish reversal candle | +2 | +2 |
| Volume spike (z >= 1) confirming | +1 | +1 |

A `BUY` thesis requires ≥ 6 points; `SELL` requires ≥ 5. Confidence is
the score normalised by the maximum possible score so it can scale the
risk-manager position size.

The LLM never decides position size — it only contributes to the
directional thesis. Risk control stays deterministic.
