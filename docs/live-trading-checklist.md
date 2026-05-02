# Live-trading checklist

> Read every line. Tick every box. Skipping a step **will lose you money**.

## Before flipping to live

- [ ] You ran `TRADING_MODE=paper` for **at least 7 days** with realistic
      market conditions and reviewed the `data/agent.db` ledger.
- [ ] You inspected `docs/halal-coins.md` and confirmed the whitelist
      matches your scholar's guidance.
- [ ] You set `MAX_POSITION_PCT`, `MAX_DAILY_LOSS_PCT`, `STOP_LOSS_PCT`,
      and `TAKE_PROFIT_PCT` in `.env` to values **you can afford to lose**.
- [ ] You created exchange API keys with **only** these permissions:
      - [x] Enable Spot Trading
      - [ ] Enable Margin (must be OFF)
      - [ ] Enable Futures (must be OFF)
      - [ ] Enable Withdrawals (must be OFF)
- [ ] You IP-whitelisted the keys to the server you'll run on.
- [ ] You moved a **small** test amount (e.g. $50–$100) into the spot
      wallet — *not your full balance*.
- [ ] You read `docs/halal-coins.md` and `docs/architecture.md`.

## Activating live mode

1. Set `TRADING_MODE=live` in `.env`.
2. Set `EXCHANGE_API_KEY` and `EXCHANGE_API_SECRET` in `.env`.
3. Create `enable_live.md` at the repo root containing exactly:

   ```
   I_HAVE_READ_THE_RISKS_AND_AUTHORIZE_LIVE_TRADING
   ```

   This file is git-ignored so it stays on the server. Without it the
   agent refuses to start in live mode.

4. Start the agent: `python -m halal_agent` (or your favourite supervisor:
   systemd, pm2, docker compose).

## Monitoring

- The dashboard runs at `http://127.0.0.1:8765/state`.
- Every trade is logged to `data/agent.db` (SQLite).
- The agent halts itself if daily loss exceeds `MAX_DAILY_LOSS_PCT`.

## Disabling live trading immediately

Two options, both safe:

1. **Stop the process** (`Ctrl-C` or `systemctl stop`). The bot no longer
   places orders. Existing positions remain on the exchange.
2. **Delete `enable_live.md`** and **restart**. The bot will refuse to
   start in live mode and you can switch back to paper.

To **flatten all positions** before stopping, set
`TAKE_PROFIT_PCT=0.0001 STOP_LOSS_PCT=0.0001` for one tick — every
position will be closed on the next loop. Or use the exchange UI directly.

## Risk acknowledgment

You understand and accept that:

- Cryptocurrency markets are volatile and can move 10%+ in minutes.
- Autonomous bots can lose money quickly through bad signals,
  flash crashes, exchange outages, or bugs.
- Past performance is not indicative of future results.
- The Sharia compliance assessment provided in `docs/halal-coins.md` is
  software opinion, not a fatwa. Confirm with your own scholar.
- You are solely responsible for any losses.
