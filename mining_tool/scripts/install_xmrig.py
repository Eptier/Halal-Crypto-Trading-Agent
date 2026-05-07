"""Standalone script to download and install XMRig."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from rich.console import Console

from mining_tool.core.xmrig_manager import INSTALL_DIR, download_xmrig
from mining_tool.utils.system_info import check_hugepages, check_mining_compatibility

console = Console()


def main() -> None:
    """Download and install XMRig."""
    console.print("[bold cyan]XMRig Installer[/bold cyan]\n")

    # Check compatibility
    console.print("[dim]Checking system compatibility...[/dim]")
    compat = check_mining_compatibility()

    if not compat["compatible"]:
        for issue in compat["issues"]:
            console.print(f"[red]Error: {issue}[/red]")
        console.print("[red]System is not compatible for mining.[/red]")
        sys.exit(1)

    for warning in compat["warnings"]:
        console.print(f"[yellow]Warning: {warning}[/yellow]")

    # Check hugepages
    hp = check_hugepages()
    if not hp["enabled"] and hp["suggestion"]:
        console.print(f"\n[yellow]Performance tip:[/yellow]\n{hp['suggestion']}")

    # Download XMRig
    console.print(f"\n[cyan]Downloading XMRig to {INSTALL_DIR}...[/cyan]")
    try:
        binary_path = download_xmrig()
        console.print(f"\n[green]XMRig installed at: {binary_path}[/green]")
        console.print("[dim]Run 'crypto-miner setup' to configure your mining settings.[/dim]")
    except Exception as e:
        console.print(f"[red]Installation failed: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
