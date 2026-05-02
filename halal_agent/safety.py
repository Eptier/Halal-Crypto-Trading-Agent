"""Safety gate for live trading.

Live mode (`TRADING_MODE=live`) requires BOTH:
  1. The env variable to be set.
  2. A committed file `enable_live.md` at the repo root containing the exact
     acknowledgment phrase. This forces the operator to make a deliberate,
     auditable, version-controlled decision before real money flows.

If either condition fails the agent refuses to start in live mode and falls
back to paper mode (or aborts, depending on caller).
"""

from __future__ import annotations

from pathlib import Path

ACK_FILENAME = "enable_live.md"
ACK_PHRASE = "I_HAVE_READ_THE_RISKS_AND_AUTHORIZE_LIVE_TRADING"


class SafetyError(RuntimeError):
    """Raised when a safety precondition for live trading is not met."""


def require_live_ack(repo_root: Path) -> None:
    """Confirm the live-trading acknowledgment file exists and is well-formed.

    Raises:
        SafetyError: if the file is missing or does not contain the phrase.
    """
    ack_path = repo_root / ACK_FILENAME
    if not ack_path.is_file():
        raise SafetyError(
            f"Live trading requested but {ACK_FILENAME!r} is missing. "
            f"Create {ack_path} containing the line {ACK_PHRASE!r} to authorize."
        )
    text = ack_path.read_text(encoding="utf-8")
    if ACK_PHRASE not in text:
        raise SafetyError(
            f"{ACK_FILENAME} does not contain the required acknowledgment phrase "
            f"{ACK_PHRASE!r}. Live trading is refused."
        )
