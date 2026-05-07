"""Rich-based CLI dashboard for terminal monitoring."""

import time

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from mining_tool.core.earnings import EarningsTracker
from mining_tool.core.xmrig_manager import XMRigManager
from mining_tool.utils.helpers import format_hashrate, format_uptime, format_usd, format_xmr
from mining_tool.utils.system_info import get_system_summary

console = Console()


def create_hashrate_panel(stats: dict) -> Panel:
    """Create hashrate display panel."""
    hashrate = stats.get("hashrate", {})
    current = hashrate.get("current", 0) or 0
    avg = hashrate.get("average", 0) or 0
    max_hr = hashrate.get("max", 0) or 0

    table = Table(show_header=False, expand=True, box=None)
    table.add_column(ratio=1)
    table.add_column(ratio=1)

    table.add_row("Current", Text(format_hashrate(current), style="bold green"))
    table.add_row("Average", Text(format_hashrate(avg), style="cyan"))
    table.add_row("Maximum", Text(format_hashrate(max_hr), style="yellow"))

    return Panel(table, title="Hashrate", border_style="green")


def create_earnings_panel(earnings: dict) -> Panel:
    """Create earnings display panel."""
    table = Table(show_header=False, expand=True, box=None)
    table.add_column(ratio=1)
    table.add_column(ratio=1)

    table.add_row("Daily (XMR)", format_xmr(earnings.get("xmr_per_day", 0)))
    daily_usd = format_usd(earnings.get("usd_per_day", 0))
    table.add_row("Daily (USD)", Text(daily_usd, style="bold green"))
    table.add_row("Monthly (XMR)", format_xmr(earnings.get("xmr_per_month", 0)))
    table.add_row(
        "Monthly (USD)",
        Text(format_usd(earnings.get("usd_per_month", 0)), style="bold green"),
    )
    table.add_row("XMR Price", format_usd(earnings.get("xmr_price_usd", 0)))

    return Panel(table, title="Estimated Earnings", border_style="yellow")


def create_shares_panel(stats: dict) -> Panel:
    """Create shares display panel."""
    shares = stats.get("shares", {})
    accepted = shares.get("accepted", 0)
    rejected = shares.get("rejected", 0)
    uptime = stats.get("uptime", 0)

    table = Table(show_header=False, expand=True, box=None)
    table.add_column(ratio=1)
    table.add_column(ratio=1)

    table.add_row("Accepted", Text(str(accepted), style="green"))
    table.add_row("Rejected", Text(str(rejected), style="red" if rejected > 0 else "green"))
    table.add_row("Uptime", format_uptime(uptime))

    connection = stats.get("connection", {})
    if isinstance(connection, dict):
        pool = connection.get("pool", "N/A")
        table.add_row("Pool", str(pool))

    return Panel(table, title="Mining Stats", border_style="cyan")


def create_system_panel(system: dict) -> Panel:
    """Create system info panel."""
    cpu = system.get("cpu", {})
    mem = system.get("memory", {})

    table = Table(show_header=False, expand=True, box=None)
    table.add_column(ratio=1)
    table.add_column(ratio=2)

    table.add_row("CPU", str(cpu.get("name", "Unknown")))
    table.add_row("Cores", f"{cpu.get('cores_physical', '?')}P / {cpu.get('cores_logical', '?')}L")
    table.add_row("RAM", f"{mem.get('total_gb', '?')} GB ({mem.get('used_percent', '?')}% used)")
    table.add_row("OS", str(system.get("os", "Unknown")))

    return Panel(table, title="System", border_style="blue")


def run_cli_dashboard(miner: XMRigManager) -> None:
    """Run the live CLI dashboard."""
    tracker = EarningsTracker()
    system = get_system_summary()

    console.print("[bold cyan]Crypto Mining Dashboard[/bold cyan]")
    console.print("[dim]Press Ctrl+C to exit[/dim]\n")

    try:
        with Live(console=console, refresh_per_second=1, screen=True) as live:
            while True:
                stats = miner.get_mining_stats()
                hashrate = (stats.get("hashrate", {}).get("current", 0)) or 0
                earnings = tracker.estimate_daily_earnings(hashrate)

                layout = Layout()
                layout.split_column(
                    Layout(name="header", size=3),
                    Layout(name="main"),
                    Layout(name="footer", size=5),
                )

                if stats.get("running"):
                    status_text = "[bold green]MINING[/bold green]"
                else:
                    status_text = "[bold red]STOPPED[/bold red]"
                layout["header"].update(
                    Panel(
                        Text.from_markup(
                            f"  Status: {status_text}  |  Refreshes every 5s  |  Ctrl+C to exit"
                        ),
                        style="bold",
                    )
                )

                layout["main"].split_row(
                    Layout(name="left"),
                    Layout(name="right"),
                )
                layout["left"].split_column(
                    Layout(create_hashrate_panel(stats)),
                    Layout(create_shares_panel(stats)),
                )
                layout["right"].split_column(
                    Layout(create_earnings_panel(earnings)),
                    Layout(create_system_panel(system)),
                )

                layout["footer"].update(
                    Panel(
                        "[dim]Mining Guide: Normal PC te CPU mining kore Monero (XMR) earn hoy. "
                        "Daily earning depend kore CPU power er upor. "
                        "Web dashboard dekhte: http://localhost:5000[/dim]",
                        title="Info",
                        border_style="dim",
                    )
                )

                live.update(layout)
                time.sleep(5)

    except KeyboardInterrupt:
        console.print("\n[yellow]Dashboard closed.[/yellow]")
