"""Convenience launcher for paper trading.

Equivalent to `TRADING_MODE=paper python -m halal_agent`.
"""

from __future__ import annotations

import os

os.environ.setdefault("TRADING_MODE", "paper")

from halal_agent.__main__ import main  # noqa: E402

if __name__ == "__main__":
    main()
