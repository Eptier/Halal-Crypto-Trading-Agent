"""Risk manager — enforces hard caps on position sizing, exposure, and loss.

This module is intentionally simple and pure: every method takes the current
state and returns either an allowed numeric size or raises `RiskRefusal`. No
side effects, easy to unit-test.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .config import Settings


class RiskRefusal(Exception):
    """Raised when a proposed action violates risk limits."""


@dataclass
class PortfolioState:
    equity: float                       # total equity in quote currency
    open_positions: int                 # count of currently open positions
    realized_pnl_today: float           # sum of realized P&L since UTC midnight
    starting_equity_today: float        # equity at UTC midnight (for % loss calc)
    today: date


class RiskManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    # ---- pre-trade checks -------------------------------------------------

    def is_trading_halted(self, state: PortfolioState) -> tuple[bool, str]:
        """Return (halted, reason). Halts if daily loss limit hit."""
        if state.starting_equity_today <= 0:
            return False, ""
        loss_pct = (state.starting_equity_today - state.equity) / state.starting_equity_today
        if loss_pct >= self.settings.max_daily_loss_pct:
            return True, (
                f"Daily loss {loss_pct * 100:.2f}% reached limit "
                f"{self.settings.max_daily_loss_pct * 100:.2f}% — auto-shutdown."
            )
        return False, ""

    def size_buy(
        self,
        state: PortfolioState,
        price: float,
        confidence: float = 1.0,
    ) -> float:
        """Compute quote-currency size for a buy. Raises RiskRefusal if blocked.

        Sizing = min(MAX_POSITION_PCT * equity, equity * confidence_factor),
        clamped to MIN_TRADE_QUOTE.
        """
        halted, reason = self.is_trading_halted(state)
        if halted:
            raise RiskRefusal(reason)
        if state.open_positions >= self.settings.max_open_positions:
            raise RiskRefusal(
                f"Max open positions ({self.settings.max_open_positions}) reached."
            )
        if price <= 0:
            raise RiskRefusal(f"Invalid price: {price}")

        cap = state.equity * self.settings.max_position_pct
        sized = cap * max(0.0, min(1.0, confidence))
        # Floor at minimum trade size; reject if even the cap is too small.
        if cap < self.settings.min_trade_quote:
            raise RiskRefusal(
                f"Available cap {cap:.2f} below MIN_TRADE_QUOTE "
                f"{self.settings.min_trade_quote:.2f}."
            )
        return max(sized, self.settings.min_trade_quote)

    # ---- post-trade exit checks ------------------------------------------

    def should_exit(
        self,
        entry_price: float,
        last_price: float,
    ) -> tuple[bool, str]:
        """Stop-loss / take-profit decision based on configured percentages."""
        if entry_price <= 0:
            return False, ""
        change = (last_price - entry_price) / entry_price
        if change <= -self.settings.stop_loss_pct:
            return True, f"stop-loss hit ({change * 100:.2f}%)"
        if change >= self.settings.take_profit_pct:
            return True, f"take-profit hit ({change * 100:.2f}%)"
        return False, ""
