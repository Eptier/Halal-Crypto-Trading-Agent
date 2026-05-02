from datetime import date

import pytest

from halal_agent.config import Settings
from halal_agent.risk import PortfolioState, RiskManager, RiskRefusal


def _settings(**overrides) -> Settings:
    base = dict(
        trading_mode="paper",
        max_position_pct=0.20,
        max_open_positions=3,
        max_daily_loss_pct=0.05,
        stop_loss_pct=0.05,
        take_profit_pct=0.10,
        min_trade_quote=10.0,
    )
    base.update(overrides)
    return Settings(**base)


def _state(**overrides) -> PortfolioState:
    base = dict(
        equity=1000.0,
        open_positions=0,
        realized_pnl_today=0.0,
        starting_equity_today=1000.0,
        today=date(2024, 1, 1),
    )
    base.update(overrides)
    return PortfolioState(**base)


def test_size_buy_caps_at_max_position_pct():
    rm = RiskManager(_settings())
    size = rm.size_buy(_state(), price=100.0, confidence=1.0)
    assert size == pytest.approx(200.0)  # 20% of 1000


def test_size_buy_scales_with_confidence():
    rm = RiskManager(_settings())
    size = rm.size_buy(_state(), price=100.0, confidence=0.5)
    assert size == pytest.approx(100.0)


def test_size_buy_floors_at_min_trade_quote():
    # Confidence so low that scaled would go below floor; should be lifted to 10.
    rm = RiskManager(_settings())
    size = rm.size_buy(_state(), price=100.0, confidence=0.001)
    assert size == 10.0


def test_size_buy_refuses_when_max_positions_hit():
    rm = RiskManager(_settings())
    with pytest.raises(RiskRefusal):
        rm.size_buy(_state(open_positions=3), price=100.0, confidence=1.0)


def test_size_buy_refuses_when_daily_loss_breached():
    rm = RiskManager(_settings())
    with pytest.raises(RiskRefusal):
        rm.size_buy(
            _state(equity=940.0, starting_equity_today=1000.0),
            price=100.0,
            confidence=1.0,
        )


def test_size_buy_refuses_when_cap_below_min_trade():
    rm = RiskManager(_settings(max_position_pct=0.01))  # 1% of 100 = 1, below min 10
    with pytest.raises(RiskRefusal):
        rm.size_buy(_state(equity=100.0, starting_equity_today=100.0), price=100.0)


def test_should_exit_stop_loss():
    rm = RiskManager(_settings())
    exit_, _ = rm.should_exit(entry_price=100.0, last_price=94.9)
    assert exit_


def test_should_exit_take_profit():
    rm = RiskManager(_settings())
    exit_, _ = rm.should_exit(entry_price=100.0, last_price=110.1)
    assert exit_


def test_should_exit_no_action_in_band():
    rm = RiskManager(_settings())
    exit_, _ = rm.should_exit(entry_price=100.0, last_price=102.0)
    assert not exit_


def test_is_trading_halted_at_threshold():
    rm = RiskManager(_settings(max_daily_loss_pct=0.05))
    halted, _ = rm.is_trading_halted(_state(equity=950.0, starting_equity_today=1000.0))
    assert halted
