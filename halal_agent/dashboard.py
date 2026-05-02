"""Tiny FastAPI dashboard for monitoring the running agent."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from .agent import Agent


def build_app(agent: Agent) -> FastAPI:
    app = FastAPI(title="Halal Trading Agent", version="0.1.0")

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/state")
    async def state() -> dict[str, Any]:
        positions = await agent.ledger.list_positions()
        trades = await agent.ledger.recent_trades(20)
        return {
            "mode": agent.settings.trading_mode,
            "exchange": agent.settings.exchange,
            "quote_currency": agent.settings.quote_currency,
            "positions": [
                {"pair": p, "base_amount": b, "avg_entry_price": e, "opened_at": t}
                for (p, b, e, t) in positions
            ],
            "recent_trades": [
                {
                    "ts": ts, "mode": m, "side": s, "pair": pair,
                    "base_amount": ba, "quote_amount": qa, "price": pr, "rationale": r,
                }
                for (ts, m, s, pair, ba, qa, pr, r) in trades
            ],
            "last_tick_halted": (
                agent.last_tick.halted if agent.last_tick else None
            ),
            "last_tick_halt_reason": (
                agent.last_tick.halt_reason if agent.last_tick else None
            ),
        }

    return app
