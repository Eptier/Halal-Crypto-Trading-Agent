"""Main agent loop. Coordinates research → strategy → risk → execution."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime

from .config import Settings
from .exchange import ExchangeAdapter
from .executor import Executor, FillReport, LiveExecutor, PaperExecutor, Position
from .halal import halal_pairs
from .ledger import Ledger
from .market_data import snapshot_from_ohlcv
from .research import ResearchAgent, build_research_agent
from .risk import PortfolioState, RiskManager, RiskRefusal
from .safety import require_live_ack

logger = logging.getLogger(__name__)


@dataclass
class TickResult:
    fills: list[FillReport]
    halted: bool
    halt_reason: str


class Agent:
    def __init__(
        self,
        settings: Settings,
        exchange: ExchangeAdapter,
        executor: Executor,
        ledger: Ledger,
        researcher: ResearchAgent,
        risk: RiskManager,
    ) -> None:
        self.settings = settings
        self.exchange = exchange
        self.executor = executor
        self.ledger = ledger
        self.researcher = researcher
        self.risk = risk
        self._starting_equity_today: float | None = None
        self._equity_day: date | None = None
        self.last_tick: TickResult | None = None

    # -- public API ---------------------------------------------------------

    async def tick(self) -> TickResult:
        """Run one full research+trade iteration across all halal pairs."""
        pairs = halal_pairs(self.settings.quote_currency)

        # 1) Pull latest market data + technical snapshots for each pair.
        snapshots = {}
        prices = {}
        for pair in pairs:
            try:
                ohlcv = await self.exchange.fetch_ohlcv(pair, timeframe="1h", limit=100)
                if len(ohlcv) < 30:
                    continue
                snap = snapshot_from_ohlcv(pair.split("/")[0], ohlcv)
                snapshots[pair] = snap
                prices[pair] = snap.last_price
            except Exception as exc:
                logger.warning("Failed to fetch %s: %s", pair, exc)

        # 2) Compute portfolio state.
        state = await self._portfolio_state(prices)
        halted, reason = self.risk.is_trading_halted(state)
        if halted:
            logger.warning("Trading halted: %s", reason)
            return TickResult([], True, reason)

        # 3) Research + decision per pair.
        fills: list[FillReport] = []
        for pair, snap in snapshots.items():
            try:
                fill = await self._evaluate_pair(pair, snap, state, prices)
                if fill:
                    fills.append(fill)
                    state = await self._portfolio_state(prices)  # refresh after a trade
            except Exception as exc:
                logger.warning("Pair %s evaluation failed: %s", pair, exc)

        # 4) Snapshot equity.
        await self.ledger.record_equity(state.equity)
        result = TickResult(fills, False, "")
        self.last_tick = result
        return result

    async def run_forever(self) -> None:
        logger.info("Agent loop starting (mode=%s)", self.settings.trading_mode)
        while True:
            try:
                result = await self.tick()
                if result.halted:
                    logger.error("Halted: %s — sleeping 1h before retry", result.halt_reason)
                    await asyncio.sleep(3600)
                    continue
            except Exception as exc:
                logger.exception("Tick failed: %s", exc)
            await asyncio.sleep(self.settings.trading_interval_seconds)

    # -- internals ----------------------------------------------------------

    async def _evaluate_pair(
        self,
        pair: str,
        snap,
        state: PortfolioState,
        prices: dict[str, float],
    ) -> FillReport | None:
        # Resolve current holding (if any).
        holding: Position | None = None
        if isinstance(self.executor, PaperExecutor):
            holding = self.executor.positions.get(pair)
        else:
            for p, base_amt, avg_px, _opened_at in await self.ledger.list_positions():
                if p == pair:
                    holding = Position(
                        pair=p,
                        base_amount=base_amt,
                        avg_entry_price=avg_px,
                    )
                    break

        # Always evaluate the research thesis. The same multi-indicator
        # confluence scoring drives BOTH entry (BUY when no position) and
        # exit (SELL when holding).
        thesis = await self.researcher.evaluate(snap)
        logger.info(
            "%s: action=%s confidence=%.2f rationale=%s",
            pair, thesis.action, thesis.confidence, thesis.rationale,
        )

        if holding is not None:
            # ---- Exit logic ------------------------------------------------
            #
            # Priority 1 (smart): research-driven SELL — only when the
            # confluence score is strong enough to be confident the move is
            # over (e.g. overbought + bearish reversal candle + MACD bearish
            # cross + EMA stack breaking down). This is the user-requested
            # "use indicators to decide when to sell".
            #
            # Priority 2 (safety net): fixed-percentage stop-loss /
            # take-profit. Fires only when the indicators DON'T paint a clear
            # picture but price has moved decisively against us (or far in our
            # favour). This is the user-requested "if the situation can't be
            # read, fall back to %".
            if thesis.action == "SELL" and thesis.confidence >= 0.4:
                logger.info(
                    "Exit %s on research SELL (conf=%.2f): %s",
                    pair, thesis.confidence, thesis.rationale,
                )
                return await self.executor.sell(pair, holding.base_amount, snap.last_price)

            should_exit, reason = self.risk.should_exit(
                holding.avg_entry_price, snap.last_price
            )
            if should_exit:
                logger.info("Exit %s on %% safety net: %s", pair, reason)
                return await self.executor.sell(pair, holding.base_amount, snap.last_price)

            return None  # hold — don't pyramid into an existing position

        # ---- Entry logic ----------------------------------------------------
        if thesis.action != "BUY":
            return None
        try:
            quote_amount = self.risk.size_buy(state, snap.last_price, thesis.confidence)
        except RiskRefusal as exc:
            logger.info("Risk refused buy on %s: %s", pair, exc)
            return None
        return await self.executor.buy(pair, quote_amount, snap.last_price)

    async def _portfolio_state(self, prices: dict[str, float]) -> PortfolioState:
        if isinstance(self.executor, PaperExecutor):
            equity = self.executor.mark_to_market(prices)
            open_positions = len(self.executor.positions)
        else:
            balance = await self.exchange.fetch_balance()
            quote = self.settings.quote_currency
            equity = float(balance.get("total", {}).get(quote, 0.0))
            for base_sym in (a.split("/")[0] for a in halal_pairs(quote)):
                qty = float(balance.get("total", {}).get(base_sym, 0.0))
                if qty > 0:
                    pair = f"{base_sym}/{quote}"
                    equity += qty * prices.get(pair, 0.0)
            open_positions = len(await self.ledger.list_positions())

        today = datetime.now(UTC).date()
        if self._equity_day != today:
            self._equity_day = today
            self._starting_equity_today = equity
        starting = self._starting_equity_today or equity
        return PortfolioState(
            equity=equity,
            open_positions=open_positions,
            realized_pnl_today=equity - starting,
            starting_equity_today=starting,
            today=today,
        )


async def build_agent(settings: Settings) -> Agent:
    """Wire up all collaborators based on settings."""
    if settings.is_live:
        require_live_ack(settings.repo_root)

    exchange = ExchangeAdapter(settings)
    await exchange.load_markets()
    ledger = Ledger(settings.db_path)
    await ledger.init()
    researcher = build_research_agent(settings)
    risk = RiskManager(settings)

    if settings.is_live:
        executor: Executor = LiveExecutor(settings, exchange, ledger)
    else:
        executor = PaperExecutor(settings, ledger, settings.paper_starting_equity)

    return Agent(settings, exchange, executor, ledger, researcher, risk)
