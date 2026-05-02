"""Trade executors. Paper-mode default; live behind safety gates."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime

from .config import Settings
from .exchange import ExchangeAdapter
from .halal import assert_halal_pair
from .ledger import Ledger, TradeRow

logger = logging.getLogger(__name__)


@dataclass
class Position:
    pair: str
    base_amount: float
    avg_entry_price: float
    opened_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class FillReport:
    pair: str
    side: str
    base_amount: float
    quote_amount: float
    price: float
    is_paper: bool


class Executor(ABC):
    """Common interface for paper / live executors."""

    @abstractmethod
    async def buy(self, pair: str, quote_amount: float, last_price: float) -> FillReport: ...

    @abstractmethod
    async def sell(self, pair: str, base_amount: float, last_price: float) -> FillReport: ...


class PaperExecutor(Executor):
    """Simulated executor — no exchange calls. Maintains in-memory cash + holdings."""

    def __init__(
        self,
        settings: Settings,
        ledger: Ledger,
        starting_equity: float,
    ) -> None:
        self.settings = settings
        self.ledger = ledger
        self.cash: float = starting_equity
        self.positions: dict[str, Position] = {}

    @property
    def equity(self) -> float:
        # Equity assuming positions were marked at their last entry price.
        # The agent loop refreshes this with live prices when computing risk state.
        positions_value = sum(p.base_amount * p.avg_entry_price for p in self.positions.values())
        return self.cash + positions_value

    def mark_to_market(self, prices: dict[str, float]) -> float:
        positions_value = 0.0
        for pair, pos in self.positions.items():
            mark = prices.get(pair, pos.avg_entry_price)
            positions_value += pos.base_amount * mark
        return self.cash + positions_value

    async def buy(self, pair: str, quote_amount: float, last_price: float) -> FillReport:
        assert_halal_pair(pair, quote=self.settings.quote_currency)
        if quote_amount > self.cash:
            raise RuntimeError(
                f"Paper buy refused: cost {quote_amount:.2f} exceeds cash {self.cash:.2f}"
            )
        base_amount = quote_amount / last_price
        # Update position (weighted avg entry price)
        existing = self.positions.get(pair)
        if existing:
            new_base = existing.base_amount + base_amount
            new_avg = (
                (existing.base_amount * existing.avg_entry_price)
                + (base_amount * last_price)
            ) / new_base
            self.positions[pair] = Position(pair, new_base, new_avg, existing.opened_at)
        else:
            self.positions[pair] = Position(pair, base_amount, last_price)
        self.cash -= quote_amount
        await self.ledger.upsert_position(
            pair, self.positions[pair].base_amount, self.positions[pair].avg_entry_price
        )
        report = FillReport(pair, "buy", base_amount, quote_amount, last_price, is_paper=True)
        await self._log(report, rationale="paper-buy")
        return report

    async def sell(self, pair: str, base_amount: float, last_price: float) -> FillReport:
        assert_halal_pair(pair, quote=self.settings.quote_currency)
        pos = self.positions.get(pair)
        if not pos or pos.base_amount < base_amount - 1e-12:
            raise RuntimeError(f"Paper sell refused: insufficient {pair} position")
        quote_amount = base_amount * last_price
        remaining = pos.base_amount - base_amount
        if remaining <= 1e-12:
            del self.positions[pair]
            await self.ledger.delete_position(pair)
        else:
            self.positions[pair] = Position(pair, remaining, pos.avg_entry_price, pos.opened_at)
            await self.ledger.upsert_position(pair, remaining, pos.avg_entry_price)
        self.cash += quote_amount
        report = FillReport(pair, "sell", base_amount, quote_amount, last_price, is_paper=True)
        await self._log(report, rationale="paper-sell")
        return report

    async def _log(self, fr: FillReport, rationale: str) -> None:
        await self.ledger.record_trade(
            TradeRow(
                ts=datetime.now(UTC).isoformat(),
                mode="paper",
                side=fr.side,
                pair=fr.pair,
                base_amount=fr.base_amount,
                quote_amount=fr.quote_amount,
                price=fr.price,
                rationale=rationale,
            )
        )


class LiveExecutor(Executor):
    """Real-money executor backed by CCXT. Halal-pair-checked on every order."""

    def __init__(self, settings: Settings, exchange: ExchangeAdapter, ledger: Ledger) -> None:
        self.settings = settings
        self.exchange = exchange
        self.ledger = ledger

    async def buy(self, pair: str, quote_amount: float, last_price: float) -> FillReport:
        assert_halal_pair(pair, quote=self.settings.quote_currency)
        order = await self.exchange.create_market_buy(pair, quote_amount)
        filled_base = float(order.get("filled") or 0.0) or float(order.get("amount") or 0.0)
        filled_quote = float(order.get("cost") or quote_amount)
        price = float(order.get("average") or order.get("price") or last_price)
        report = FillReport(pair, "buy", filled_base, filled_quote, price, is_paper=False)

        # Persist the position so the agent can enforce stop-loss / take-profit /
        # max-open-positions on the next tick. Without this, the live agent would
        # be unable to detect existing holdings and would re-buy every cycle.
        if filled_base > 0:
            existing = await self.ledger.get_position(pair)
            if existing is not None:
                existing_base, existing_avg = existing
                new_base = existing_base + filled_base
                new_avg = (
                    (existing_base * existing_avg + filled_base * price) / new_base
                    if new_base > 0
                    else price
                )
            else:
                new_base = filled_base
                new_avg = price
            await self.ledger.upsert_position(pair, new_base, new_avg)
        else:
            logger.warning("Live buy on %s returned filled_base=0; position not recorded", pair)

        await self._log(report, rationale="live-buy")
        return report

    async def sell(self, pair: str, base_amount: float, last_price: float) -> FillReport:
        assert_halal_pair(pair, quote=self.settings.quote_currency)
        order = await self.exchange.create_market_sell(pair, base_amount)
        filled_base = float(order.get("filled") or base_amount)
        filled_quote = float(order.get("cost") or filled_base * last_price)
        price = float(order.get("average") or order.get("price") or last_price)
        report = FillReport(pair, "sell", filled_base, filled_quote, price, is_paper=False)

        # Update / clear the persisted position so subsequent ticks reflect reality.
        existing = await self.ledger.get_position(pair)
        if existing is not None:
            existing_base, existing_avg = existing
            remaining = existing_base - filled_base
            if remaining <= 1e-12:
                await self.ledger.delete_position(pair)
            else:
                await self.ledger.upsert_position(pair, remaining, existing_avg)
        else:
            logger.warning(
                "Live sell on %s but no recorded position; nothing to update", pair
            )

        await self._log(report, rationale="live-sell")
        return report

    async def _log(self, fr: FillReport, rationale: str) -> None:
        await self.ledger.record_trade(
            TradeRow(
                ts=datetime.now(UTC).isoformat(),
                mode="live",
                side=fr.side,
                pair=fr.pair,
                base_amount=fr.base_amount,
                quote_amount=fr.quote_amount,
                price=fr.price,
                rationale=rationale,
            )
        )
