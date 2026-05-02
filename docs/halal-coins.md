# Halal coin whitelist — sources & rationale

This file documents *why* each asset on the whitelist (`halal_agent/halal.py`)
is considered Shariah-compliant for spot trading, and why several common
coins are deliberately excluded.

> **Disclaimer**: This is software, not a fatwa. Confirm with your own
> qualified scholar before deploying live. The list can be **tightened** by
> editing `halal_agent/halal.py` directly; it cannot be loosened at runtime.

## Methodology

A coin is included only if **all** of the following hold:

1. **No riba (interest)** — the protocol's core value proposition is *not*
   lending, borrowing, or yield generation against an interest rate.
2. **No gharar (excessive uncertainty)** — the asset has clear utility,
   transparent supply, and is not effectively a gambling chip.
3. **No haram industry exposure** — the project does not derive its income
   from gambling, alcohol, adult content, conventional insurance, etc.
4. **Spot-only use** — we never margin, short, lend, or stake on yield.
   This is enforced in code (`halal_agent/exchange.py`).

## Primary source

[**Shariyah Review Bureau (SRB)**](https://shariyah.net/cryptocurrency/) maintains
a public assessment of major cryptocurrencies, classifying each as Compliant,
Neutral, or Non-Compliant. SRB is licensed by the Central Bank of Bahrain and
is a recognised Sharia advisor for several Islamic financial institutions.

## Cross-checks

- **Mufti Faraz Adam** (Amanah Advisors) — written opinions on BTC and ETH.
- **Joe Bradford** — practical guidance for Muslim retail traders.
- **Islamic Finance Guru (IFG)** — crypto guidance for UK-based investors.

## Whitelist (as of project inception)

| Symbol | Name              | SRB status (asof)  | Rationale                                                                |
|--------|-------------------|--------------------|--------------------------------------------------------------------------|
| BTC    | Bitcoin           | Compliant Aug-2021 | Decentralised digital asset; no inherent riba.                           |
| ETH    | Ethereum          | Compliant Aug-2021 | Smart-contract platform utility token.                                   |
| ADA    | Cardano           | Compliant Aug-2021 | Proof-of-stake utility token.                                            |
| XRP    | XRP (Ripple)      | Compliant Aug-2021 | Settlement / payment-network utility token.                              |
| XLM    | Stellar           | Compliant Aug-2021 | Cross-border payments utility token.                                     |
| ALGO   | Algorand          | Compliant Dec-2022 | Pure proof-of-stake utility token.                                       |
| AVAX   | Avalanche         | Compliant Sep-2022 | Smart-contract platform utility token.                                   |
| DOT    | Polkadot          | Compliant Sep-2022 | Multi-chain utility / governance token.                                  |
| MATIC  | Polygon           | Compliant Sep-2022 | Ethereum scaling utility token.                                          |
| XTZ    | Tezos             | Compliant Dec-2022 | On-chain governance utility token.                                       |
| LTC    | Litecoin          | Compliant Dec-2022 | Payment-focused fork of Bitcoin.                                         |

## Quote currency policy

The agent quotes prices in a stablecoin. Three options:

| Quote | Status | Note |
|-------|--------|------|
| USDT  | SRB compliant Aug-2021 | Default. Some scholars dispute it because Tether's reserves include interest-bearing instruments. |
| USDC  | Allowed | Issued by Circle. Some scholars prefer it over USDT for transparency. |
| BUSD  | Allowed | Binance USD (sunsetting on some exchanges). |
| DAI   | Allowed | Decentralised stablecoin. |

Set `QUOTE_CURRENCY` in `.env` to your preference.

## Out of scope (not whitelisted)

| Symbol | Why excluded |
|--------|--------------|
| AAVE   | DeFi lending protocol — the entire business model is interest. |
| COMP   | Compound — same as AAVE. |
| MKR    | Maker — DAO with debt-issuance and liquidation auctions. |
| XMR    | Monero — privacy coin; mixed scholarly views. Excluded conservatively. |
| GRT    | Indexing service revenues unclear; reassessment required. |
| Yield-bearing tokens (stETH, rETH, cbETH, etc.) | Riba-like staking returns. |
| Gambling / prediction-market tokens | Maysir (gambling) is haram. |
| Memecoins with no utility | Gharar (excessive uncertainty). |

## How to update this list

If your scholar approves additional assets:

1. Edit `halal_agent/halal.py` and add a `HalalAsset(...)` entry with the
   `source` field citing the fatwa.
2. Update this document with the rationale.
3. Run the test suite: `pytest tests/test_halal.py`.
4. Open a pull request.

To **remove** an asset (e.g. SRB downgrades it), simply delete its entry
from `HALAL_ASSETS` and rerun the tests.
