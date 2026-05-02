"""Hard-coded Shariah-compliant asset whitelist.

This module is the *single source of truth* for which assets the agent is
allowed to trade. The list is intentionally hard-coded (not configurable
at runtime) to make it impossible for a misconfigured or malicious .env
file to introduce a haram asset.

Sources & methodology
---------------------
The base list is drawn from the **Shariyah Review Bureau** (https://shariyah.net)
crypto assessment, which classifies each coin as Compliant / Neutral /
Non-Compliant under Sharia. Only coins explicitly assessed as **Compliant**
on a recent SRB review are included.

Cross-checks:
- Mufti Faraz Adam (Amanah Advisors) — published opinions on BTC/ETH.
- Joe Bradford — practical guidance for Muslim retail traders.
- Islamic Finance Guru (IFG) crypto guidance.

Out of scope (not included), with reasoning:
- AAVE, COMP — DeFi lending protocols whose core function is interest (riba).
- Stablecoins backed by interest-bearing reserves (status disputed; we do
  allow USDT as a *quote* pair because SRB classifies it as Compliant
  Aug-2021, but users may switch QUOTE_CURRENCY to USDC/BUSD per their
  own scholar's guidance).
- Gambling / prediction-market tokens.
- Privacy coins (XMR) — mixed scholarly opinion; excluded conservatively.
- Yield-bearing / staking-derivative tokens (stETH, etc.) — riba-like.

Disclaimer: This is software, not a fatwa. Confirm with your own scholar
before deploying live. The list can be tightened (never broadened at
runtime) by editing this file.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HalalAsset:
    symbol: str
    name: str
    rationale: str
    source: str


# fmt: off
HALAL_ASSETS: tuple[HalalAsset, ...] = (
    HalalAsset("BTC",   "Bitcoin",
               "Decentralized digital asset; no riba, no gharar in the asset itself.",
               "Shariyah Review Bureau (Aug 2021); Mufti Faraz Adam"),
    HalalAsset("ETH",   "Ethereum",
               "Smart-contract platform; underlying token is utility-based.",
               "Shariyah Review Bureau (Aug 2021)"),
    HalalAsset("ADA",   "Cardano",
               "Proof-of-stake utility token; protocol does not engage in riba.",
               "Shariyah Review Bureau (Aug 2021)"),
    HalalAsset("XRP",   "XRP (Ripple)",
               "Settlement / utility token; payment-network use case.",
               "Shariyah Review Bureau (Aug 2021)"),
    HalalAsset("XLM",   "Stellar Lumens",
               "Cross-border payments utility token.",
               "Shariyah Review Bureau (Aug 2021)"),
    HalalAsset("ALGO",  "Algorand",
               "Pure proof-of-stake utility token.",
               "Shariyah Review Bureau (Dec 2022)"),
    HalalAsset("AVAX",  "Avalanche",
               "Smart-contract platform utility token.",
               "Shariyah Review Bureau (Sep 2022)"),
    HalalAsset("DOT",   "Polkadot",
               "Multichain utility / governance token.",
               "Shariyah Review Bureau (Sep 2022, reassessed compliant)"),
    HalalAsset("MATIC", "Polygon",
               "Ethereum scaling utility token.",
               "Shariyah Review Bureau (Sep 2022)"),
    HalalAsset("XTZ",   "Tezos",
               "On-chain governance utility token.",
               "Shariyah Review Bureau (Dec 2022)"),
    HalalAsset("LTC",   "Litecoin",
               "Payment-focused fork of Bitcoin.",
               "Shariyah Review Bureau (Dec 2022)"),
)
# fmt: on


HALAL_SYMBOLS: frozenset[str] = frozenset(a.symbol for a in HALAL_ASSETS)


# Quote currencies considered acceptable for halal spot pairs.
# USDT is included on Shariyah Review Bureau's Aug-2021 compliant list.
# Users uncomfortable with USDT can switch QUOTE_CURRENCY to BUSD/USDC.
ALLOWED_QUOTE_CURRENCIES: frozenset[str] = frozenset({"USDT", "USDC", "BUSD", "DAI"})


class HalalViolation(ValueError):
    """Raised when an attempt is made to trade a non-whitelisted asset."""


def is_halal(symbol: str) -> bool:
    """Return True if `symbol` (e.g. 'BTC') is on the halal whitelist."""
    return symbol.upper() in HALAL_SYMBOLS


def assert_halal_pair(pair: str, *, quote: str) -> None:
    """Validate a market pair like 'BTC/USDT'. Raises HalalViolation if invalid.

    Args:
        pair: Market symbol in CCXT 'BASE/QUOTE' format.
        quote: Configured quote currency; must match the pair's quote.
    """
    if "/" not in pair:
        raise HalalViolation(f"Invalid pair format (expected BASE/QUOTE): {pair!r}")
    base, q = pair.split("/", 1)
    base_u, q_u, quote_u = base.upper(), q.upper(), quote.upper()
    if q_u != quote_u:
        raise HalalViolation(f"Pair {pair!r} quote {q_u} does not match configured quote {quote_u}")
    if quote_u not in ALLOWED_QUOTE_CURRENCIES:
        raise HalalViolation(
            f"Quote currency {quote_u} is not on the allowed list "
            f"({sorted(ALLOWED_QUOTE_CURRENCIES)})"
        )
    if base_u not in HALAL_SYMBOLS:
        raise HalalViolation(
            f"Asset {base_u} is not on the halal whitelist. "
            f"Allowed: {sorted(HALAL_SYMBOLS)}"
        )


def halal_pairs(quote: str) -> list[str]:
    """Return all whitelisted base assets paired with the given quote."""
    return [f"{a.symbol}/{quote.upper()}" for a in HALAL_ASSETS]
