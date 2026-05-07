"""Helper utilities for the mining tool."""

import time


def format_hashrate(hashrate_hs: float) -> str:
    """Format hashrate with appropriate unit."""
    if hashrate_hs >= 1_000_000:
        return f"{hashrate_hs / 1_000_000:.2f} MH/s"
    elif hashrate_hs >= 1_000:
        return f"{hashrate_hs / 1_000:.2f} KH/s"
    else:
        return f"{hashrate_hs:.2f} H/s"


def format_uptime(seconds: int) -> str:
    """Format uptime in human-readable format."""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}m {secs}s"
    elif seconds < 86400:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"
    else:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        return f"{days}d {hours}h"


def format_xmr(amount: float) -> str:
    """Format XMR amount."""
    if amount < 0.0001:
        return f"{amount:.10f} XMR"
    elif amount < 1:
        return f"{amount:.8f} XMR"
    else:
        return f"{amount:.6f} XMR"


def format_usd(amount: float) -> str:
    """Format USD amount."""
    if amount < 0.01:
        return f"${amount:.6f}"
    return f"${amount:.2f}"


def validate_xmr_address(address: str) -> bool:
    """Basic validation of Monero wallet address."""
    if not address:
        return False
    if len(address) == 95 and address.startswith("4"):
        return True
    if len(address) == 106 and address.startswith("4"):
        return True
    if len(address) == 95 and address.startswith("8"):
        return True
    return False


def get_timestamp() -> str:
    """Get current timestamp as formatted string."""
    return time.strftime("%Y-%m-%d %H:%M:%S")
