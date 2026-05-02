# halal-trading-agent

> Autonomous, Shariah-compliant cryptocurrency trading agent.
> **Spot-only. Halal-whitelisted. Paper-mode default. Live-mode safety-gated.**

---

## ⚠ Read first

This bot trades real money when you switch it to live mode. Crypto markets
are volatile and autonomous bots can lose money quickly. **Do not skip the
checklist in [`docs/live-trading-checklist.md`](docs/live-trading-checklist.md).**

This is software, not a fatwa. Confirm the asset whitelist with your own
qualified scholar — see [`docs/halal-coins.md`](docs/halal-coins.md).

---

## What it does

1. Every tick, fetches OHLCV data for each Sharia-compliant spot pair from
   your configured exchange (Binance by default, any CCXT-supported venue
   works).
2. Computes RSI / EMA / MACD indicators and feeds them to a research agent
   (rule-based by default; OpenAI-backed if `OPENAI_API_KEY` is set).
3. The research agent emits a `BUY / HOLD / SELL` thesis with a confidence
   score.
4. A deterministic risk manager sizes positions (capped at
   `MAX_POSITION_PCT` of equity), enforces a maximum number of open
   positions, and halts trading if daily loss exceeds
   `MAX_DAILY_LOSS_PCT`.
5. Trades are executed against either an in-memory paper executor
   (default) or a real CCXT spot account (live mode, guarded by an
   acknowledgment file).
6. Every fill, position, and equity snapshot is logged to a SQLite ledger
   and exposed via a small FastAPI dashboard.

## Halal compliance — at a glance

- **Whitelist hard-coded** in [`halal_agent/halal.py`](halal_agent/halal.py)
  and validated on every order. Source: Shariyah Review Bureau (cross-
  referenced with Mufti Faraz Adam / Amanah Advisors and Islamic Finance
  Guru). See [`docs/halal-coins.md`](docs/halal-coins.md) for sources.
- **Spot only** — CCXT client is configured with `defaultType: 'spot'`. No
  margin / futures / leverage / shorting / lending code paths exist.
- **No yield, no staking, no lending tokens** (AAVE, COMP, MKR, etc.) — explicitly
  excluded as the project's core function would generate riba.

## Quickstart (paper mode, no keys required)

```bash
# 1. Install deps (uv recommended)
uv sync

# 2. Copy the env template
cp .env.example .env
# (default values work for paper mode)

# 3. Run a single tick to verify everything wires up
uv run python -m halal_agent --once

# 4. Run the live loop + dashboard
uv run python -m halal_agent
# Dashboard: http://127.0.0.1:8765/state
```

In paper mode the bot uses real market data from the exchange but fills
orders in memory against a simulated `PAPER_STARTING_EQUITY`. No funds
move. You can keep this running for a week and inspect `data/agent.db`
to see how the strategy performs before flipping to live.

## Going live (after paper validation)

Read [`docs/live-trading-checklist.md`](docs/live-trading-checklist.md) end
to end. Summary:

1. Run paper mode for at least a week.
2. Create exchange API keys (spot only, no margin / futures / withdrawals).
3. Set `TRADING_MODE=live`, `EXCHANGE_API_KEY`, `EXCHANGE_API_SECRET` in
   `.env`.
4. Create `enable_live.md` at the repo root containing exactly:

       I_HAVE_READ_THE_RISKS_AND_AUTHORIZE_LIVE_TRADING

   Without that file, the agent refuses to start in live mode.

5. Start the agent. Watch the dashboard.

## Configuration

See [`.env.example`](.env.example) for every setting and its default. The
main knobs:

| Variable | Default | Meaning |
|----------|---------|---------|
| `TRADING_MODE` | `paper` | `paper` or `live`. |
| `EXCHANGE` | `binance` | Any CCXT spot exchange. |
| `QUOTE_CURRENCY` | `USDT` | Stablecoin to quote against (USDT/USDC/BUSD/DAI). |
| `PAPER_STARTING_EQUITY` | `1000` | Initial paper-mode balance. |
| `MAX_POSITION_PCT` | `0.20` | Max % of equity per single trade. |
| `MAX_OPEN_POSITIONS` | `3` | Max simultaneous positions. |
| `MAX_DAILY_LOSS_PCT` | `0.05` | Auto-shutdown threshold. |
| `STOP_LOSS_PCT` | `0.05` | Per-position stop-loss. |
| `TAKE_PROFIT_PCT` | `0.10` | Per-position take-profit. |
| `OPENAI_API_KEY` | _(unset)_ | If set, enables LLM research agent. |

## Architecture

See [`docs/architecture.md`](docs/architecture.md) for the full module map.

## Tests

```bash
uv run pytest
uv run ruff check halal_agent tests
uv run mypy halal_agent
```

Tests cover the safety-critical modules (halal whitelist, safety ack gate,
risk manager, paper executor, indicators, rule-based researcher).

## Project layout

```
halal_agent/        agent code
tests/              pytest suite
docs/               halal sources, architecture, live-trading checklist
scripts/            one-off helpers
```

## Disclaimer

Provided "as is" without warranty of any kind. The author is not a
licensed financial adviser nor a Mufti. Use at your own risk.
