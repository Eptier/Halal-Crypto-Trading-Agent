"""CLI entry point."""

from __future__ import annotations

import argparse
import asyncio
import logging

import uvicorn

from .agent import build_agent
from .config import get_settings
from .dashboard import build_app


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


async def _run(no_dashboard: bool) -> None:
    settings = get_settings()
    _configure_logging(settings.log_level)
    agent = await build_agent(settings)
    tasks: list[asyncio.Task] = [asyncio.create_task(agent.run_forever())]

    if not no_dashboard:
        app = build_app(agent)
        config = uvicorn.Config(
            app,
            host=settings.dashboard_host,
            port=settings.dashboard_port,
            log_level=settings.log_level.lower(),
        )
        server = uvicorn.Server(config)
        tasks.append(asyncio.create_task(server.serve()))

    try:
        await asyncio.gather(*tasks)
    finally:
        await agent.exchange.close()


def main() -> None:
    parser = argparse.ArgumentParser(prog="halal-agent")
    parser.add_argument(
        "--no-dashboard", action="store_true", help="Run the trading loop only."
    )
    parser.add_argument(
        "--once", action="store_true", help="Run a single tick and exit (for testing)."
    )
    args = parser.parse_args()

    if args.once:
        asyncio.run(_run_once())
    else:
        asyncio.run(_run(args.no_dashboard))


async def _run_once() -> None:
    settings = get_settings()
    _configure_logging(settings.log_level)
    agent = await build_agent(settings)
    try:
        result = await agent.tick()
        print(f"Tick complete: fills={len(result.fills)} halted={result.halted}")
        for f in result.fills:
            print(
                f"  {f.side.upper()} {f.pair} base={f.base_amount:.6f} "
                f"quote={f.quote_amount:.2f} price={f.price:.4f} "
                f"({'paper' if f.is_paper else 'LIVE'})"
            )
    finally:
        await agent.exchange.close()


if __name__ == "__main__":
    main()
