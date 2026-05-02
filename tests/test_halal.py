import pytest

from halal_agent.halal import (
    ALLOWED_QUOTE_CURRENCIES,
    HALAL_SYMBOLS,
    HalalViolation,
    assert_halal_pair,
    halal_pairs,
    is_halal,
)


def test_known_halal_assets():
    for sym in ("BTC", "ETH", "ADA", "XLM", "ALGO", "XRP"):
        assert is_halal(sym)


def test_haram_lending_tokens_rejected():
    # AAVE, COMP — DeFi lending (riba). Must NOT be on the whitelist.
    assert not is_halal("AAVE")
    assert not is_halal("COMP")
    assert not is_halal("MKR")


def test_unknown_symbol_rejected():
    assert not is_halal("DOGEINU_SCAM")


def test_assert_halal_pair_happy_path():
    assert_halal_pair("BTC/USDT", quote="USDT")


def test_assert_halal_pair_quote_mismatch():
    with pytest.raises(HalalViolation):
        assert_halal_pair("BTC/USDT", quote="USDC")


def test_assert_halal_pair_haram_base():
    with pytest.raises(HalalViolation):
        assert_halal_pair("AAVE/USDT", quote="USDT")


def test_assert_halal_pair_unknown_quote():
    with pytest.raises(HalalViolation):
        assert_halal_pair("BTC/EUR", quote="EUR")


def test_assert_halal_pair_bad_format():
    with pytest.raises(HalalViolation):
        assert_halal_pair("BTCUSDT", quote="USDT")


def test_halal_pairs_helper():
    pairs = halal_pairs("USDT")
    assert "BTC/USDT" in pairs
    assert all(p.endswith("/USDT") for p in pairs)
    assert len(pairs) == len(HALAL_SYMBOLS)


def test_allowed_quote_currencies_include_common_stablecoins():
    assert "USDT" in ALLOWED_QUOTE_CURRENCIES
    assert "USDC" in ALLOWED_QUOTE_CURRENCIES
