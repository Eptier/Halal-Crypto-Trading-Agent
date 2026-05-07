"""Main entry point for the Crypto Mining Tool."""

import argparse
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from mining_tool.config.settings import MINING_POOLS, SUPPORTED_COINS, MinerConfig
from mining_tool.core.earnings import EarningsTracker
from mining_tool.core.xmrig_manager import XMRigManager
from mining_tool.dashboard.cli_dashboard import run_cli_dashboard
from mining_tool.dashboard.web_dashboard import run_dashboard
from mining_tool.utils.helpers import format_hashrate, format_usd, validate_xmr_address
from mining_tool.utils.system_info import (
    check_mining_compatibility,
    estimate_hashrate,
    get_optimal_threads,
    get_system_summary,
)

console = Console()


def cmd_setup(args: argparse.Namespace) -> None:
    """Interactive setup wizard."""
    console.print(Panel("[bold cyan]Crypto Mining Tool - Setup Wizard[/bold cyan]\n"
                        "[dim]আপনার mining configuration সেটআপ করুন[/dim]"))

    config = MinerConfig.load()

    # Wallet address
    console.print("\n[bold]1. Wallet Address (XMR)[/bold]")
    console.print(
        "[dim]Monero wallet address দিন।"
        " আপনার কাছে না থাকলে, MyMonero বা Cake Wallet থেকে তৈরি করুন।[/dim]"
    )
    wallet = input(f"Wallet [{config.wallet_address or 'none'}]: ").strip()
    if wallet:
        if not validate_xmr_address(wallet):
            console.print(
                "[yellow]Warning: Address format doesn't look standard."
                " Continuing anyway...[/yellow]"
            )
        config.wallet_address = wallet

    # Pool selection
    console.print("\n[bold]2. Mining Pool Select করুন[/bold]")
    pool_table = Table(show_header=True)
    pool_table.add_column("Key", style="cyan")
    pool_table.add_column("Pool Name")
    pool_table.add_column("Fee")
    pool_table.add_column("Description")
    for key, pool in MINING_POOLS.items():
        pool_table.add_row(key, pool["name"], f"{pool['fee']}%", pool["description"])
    console.print(pool_table)

    pool_choice = input(f"Pool [{config.pool}]: ").strip().lower()
    if pool_choice and pool_choice in MINING_POOLS:
        config.pool = pool_choice

    # Worker name
    console.print("\n[bold]3. Worker Name[/bold]")
    console.print("[dim]আপনার PC এর নাম দিন (pool dashboard এ দেখাবে)[/dim]")
    worker = input(f"Worker name [{config.worker_name}]: ").strip()
    if worker:
        config.worker_name = worker

    # CPU settings
    console.print("\n[bold]4. CPU Settings[/bold]")
    optimal = get_optimal_threads()
    console.print(f"[dim]Recommended threads: {optimal} (0 = auto)[/dim]")
    threads_input = input(f"Threads [{config.threads}]: ").strip()
    if threads_input.isdigit():
        config.threads = int(threads_input)

    cpu_limit = input(f"Max CPU usage % [{config.cpu_max_usage}]: ").strip()
    if cpu_limit.isdigit():
        config.cpu_max_usage = min(100, max(10, int(cpu_limit)))

    # Dashboard port
    console.print("\n[bold]5. Dashboard Settings[/bold]")
    port_input = input(f"Dashboard port [{config.dashboard_port}]: ").strip()
    if port_input.isdigit():
        config.dashboard_port = int(port_input)

    # Save config
    config.save()
    console.print("\n[green]Config saved![/green]")
    console.print(f"[dim]Config file: {config.save.__func__.__code__.co_filename}[/dim]")

    # Show summary
    console.print(Panel(
        f"Wallet: {config.wallet_address[:20]}...{config.wallet_address[-10:]}\n"
        f"Pool: {config.get_pool_name()} ({config.get_pool_url()})\n"
        f"Worker: {config.worker_name}\n"
        f"CPU: {config.cpu_max_usage}% max, {config.threads or 'auto'} threads\n"
        f"Dashboard: http://localhost:{config.dashboard_port}",
        title="Configuration Summary",
        border_style="green",
    ))

    console.print(
        "\n[bold cyan]Setup complete!"
        " Run 'crypto-miner start' to begin mining.[/bold cyan]"
    )


def cmd_start(args: argparse.Namespace) -> None:
    """Start mining."""
    config = MinerConfig.load()

    if not config.wallet_address:
        console.print("[red]Error: No wallet address configured![/red]")
        console.print("Run 'crypto-miner setup' first, or use --wallet flag.")
        sys.exit(1)

    if args.wallet:
        config.wallet_address = args.wallet
    if args.pool:
        config.pool = args.pool
    if args.threads:
        config.threads = args.threads

    # System check
    compat = check_mining_compatibility()
    if not compat["compatible"]:
        for issue in compat["issues"]:
            console.print(f"[red]Error: {issue}[/red]")
        sys.exit(1)
    for warning in compat["warnings"]:
        console.print(f"[yellow]Warning: {warning}[/yellow]")

    # Start miner
    manager = XMRigManager(config)

    console.print("[cyan]Setting up XMRig...[/cyan]")
    if not manager.setup():
        console.print("[red]Failed to set up XMRig. Check your internet connection.[/red]")
        sys.exit(1)

    console.print(f"[cyan]Connecting to {config.get_pool_name()}...[/cyan]")
    if not manager.start():
        console.print("[red]Failed to start mining.[/red]")
        sys.exit(1)

    # Start dashboard
    console.print("[green]Mining started![/green]")

    if args.no_dashboard:
        console.print("[dim]Dashboard disabled. Press Ctrl+C to stop.[/dim]")
        try:
            manager.process.wait()
        except KeyboardInterrupt:
            manager.stop()
    elif args.web_only:
        run_dashboard(manager, config.dashboard_port)
        console.print(f"[green]Web dashboard: http://localhost:{config.dashboard_port}[/green]")
        try:
            manager.process.wait()
        except KeyboardInterrupt:
            manager.stop()
    else:
        run_dashboard(manager, config.dashboard_port)
        console.print(f"[dim]Web dashboard: http://localhost:{config.dashboard_port}[/dim]")
        run_cli_dashboard(manager)
        manager.stop()


def cmd_stop(args: argparse.Namespace) -> None:
    """Stop mining."""
    config = MinerConfig.load()
    manager = XMRigManager(config)
    if manager.stop():
        console.print("[green]Mining stopped.[/green]")
    else:
        console.print("[yellow]No running miner found.[/yellow]")


def cmd_status(args: argparse.Namespace) -> None:
    """Show mining status."""
    config = MinerConfig.load()
    manager = XMRigManager(config)
    tracker = EarningsTracker()

    if not manager.is_running():
        console.print("[yellow]Miner is not running.[/yellow]")
        return

    stats = manager.get_mining_stats()
    hashrate = stats["hashrate"]["current"] or 0
    earnings = tracker.estimate_daily_earnings(hashrate)

    table = Table(title="Mining Status", show_header=False)
    table.add_column("", style="cyan")
    table.add_column("")

    table.add_row("Status", "[green]Running[/green]")
    table.add_row("Hashrate", format_hashrate(hashrate))
    table.add_row("Shares (Accepted)", str(stats["shares"]["accepted"]))
    table.add_row("Shares (Rejected)", str(stats["shares"]["rejected"]))
    daily = f"{format_usd(earnings['usd_per_day'])} ({earnings['xmr_per_day']:.8f} XMR)"
    monthly = f"{format_usd(earnings['usd_per_month'])} ({earnings['xmr_per_month']:.8f} XMR)"
    table.add_row("Daily Earning", daily)
    table.add_row("Monthly Earning", monthly)
    table.add_row("XMR Price", format_usd(earnings.get("xmr_price_usd", 0)))

    console.print(table)


def cmd_benchmark(args: argparse.Namespace) -> None:
    """Run system benchmark and show estimated earnings."""
    console.print("[cyan]Running system benchmark...[/cyan]\n")

    system = get_system_summary()
    cpu = system["cpu"]
    tracker = EarningsTracker()

    optimal_threads = get_optimal_threads()
    est_hashrate = estimate_hashrate(cpu["name"], optimal_threads)
    earnings = tracker.estimate_daily_earnings(est_hashrate)

    table = Table(title="System Benchmark Results", show_header=False)
    table.add_column("", style="cyan", width=25)
    table.add_column("")

    table.add_row("CPU", cpu["name"])
    table.add_row("Cores (P/L)", f"{cpu['cores_physical']} / {cpu['cores_logical']}")
    table.add_row("RAM", f"{system['memory']['total_gb']} GB")
    table.add_row("Optimal Threads", str(optimal_threads))
    table.add_row("", "")
    table.add_row("Est. Hashrate", format_hashrate(est_hashrate))
    table.add_row("Est. Daily (USD)", format_usd(earnings["usd_per_day"]))
    table.add_row("Est. Monthly (USD)", format_usd(earnings["usd_per_month"]))
    table.add_row("XMR Price", format_usd(earnings.get("xmr_price_usd", 0)))

    console.print(table)

    console.print("\n[dim]Note: These are rough estimates. Actual results depend on "
                  "network difficulty, pool luck, and CPU performance.[/dim]")
    console.print("[dim]দ্রষ্টব্য: এগুলো আনুমানিক হিসাব। আসল ফলাফল network difficulty, "
                  "pool luck, এবং CPU performance এর উপর নির্ভর করে।[/dim]")


def cmd_info(args: argparse.Namespace) -> None:
    """Show supported coins and pools."""
    console.print(Panel("[bold]Supported Coins (CPU Mining)[/bold]"))
    coin_table = Table(show_header=True)
    coin_table.add_column("Symbol", style="cyan")
    coin_table.add_column("Name")
    coin_table.add_column("Algorithm")
    coin_table.add_column("Description")
    for coin in SUPPORTED_COINS.values():
        coin_table.add_row(coin["symbol"], coin["name"], coin["algorithm"], coin["description"])
    console.print(coin_table)

    console.print(Panel("[bold]Available Mining Pools[/bold]"))
    pool_table = Table(show_header=True)
    pool_table.add_column("Key", style="cyan")
    pool_table.add_column("Name")
    pool_table.add_column("Fee")
    pool_table.add_column("Description")
    for key, pool in MINING_POOLS.items():
        pool_table.add_row(key, pool["name"], f"{pool['fee']}%", pool["description"])
    console.print(pool_table)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="crypto-miner",
        description="CPU Crypto Mining Tool - Normal PC te mine korun, earning korun!",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Setup
    subparsers.add_parser("setup", help="Interactive setup wizard (সেটআপ)")

    # Start
    start_parser = subparsers.add_parser("start", help="Start mining (মাইনিং শুরু)")
    start_parser.add_argument("--wallet", "-w", help="XMR wallet address")
    start_parser.add_argument("--pool", "-p", help="Mining pool name")
    start_parser.add_argument("--threads", "-t", type=int, help="Number of CPU threads")
    start_parser.add_argument("--no-dashboard", action="store_true", help="Disable dashboard")
    start_parser.add_argument("--web-only", action="store_true", help="Web dashboard only (no CLI)")

    # Stop
    subparsers.add_parser("stop", help="Stop mining (মাইনিং বন্ধ)")

    # Status
    subparsers.add_parser("status", help="Show mining status (স্ট্যাটাস)")

    # Benchmark
    subparsers.add_parser("benchmark", help="Run benchmark (বেঞ্চমার্ক)")

    # Info
    subparsers.add_parser("info", help="Show coins & pools info (তথ্য)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        console.print("\n[bold cyan]Quick Start:[/bold cyan]")
        console.print("  1. crypto-miner setup     (config সেটআপ)")
        console.print("  2. crypto-miner benchmark  (PC test)")
        console.print("  3. crypto-miner start      (mining শুরু)")
        return

    commands = {
        "setup": cmd_setup,
        "start": cmd_start,
        "stop": cmd_stop,
        "status": cmd_status,
        "benchmark": cmd_benchmark,
        "info": cmd_info,
    }

    cmd_func = commands.get(args.command)
    if cmd_func:
        cmd_func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
