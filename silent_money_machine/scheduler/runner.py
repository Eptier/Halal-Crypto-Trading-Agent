"""APScheduler setup — configures and starts all recurring automation jobs."""

from __future__ import annotations

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from silent_money_machine.core.config import settings
from silent_money_machine.scheduler.jobs import (
    job_daily_outreach,
    job_generate_content,
    job_reset_saas_usage,
)

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


_background_tasks: set[asyncio.Task[None]] = set()


def _wrap_async(coro_func):  # type: ignore[no-untyped-def]
    """Wrap an async function so APScheduler can call it."""
    def wrapper() -> None:
        loop = asyncio.get_event_loop()
        task = loop.create_task(coro_func())
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)
    return wrapper


def configure_scheduler() -> None:
    """Register all recurring jobs."""
    scheduler.add_job(
        _wrap_async(job_generate_content),
        CronTrigger(hour=settings.content_generation_hour, minute=0),
        id="content_generation",
        name="Daily content generation for all clients",
        replace_existing=True,
    )

    scheduler.add_job(
        _wrap_async(job_daily_outreach),
        CronTrigger(hour=settings.outreach_hour, minute=0),
        id="daily_outreach",
        name="Daily cold email and follow-up outreach",
        replace_existing=True,
    )

    scheduler.add_job(
        _wrap_async(job_reset_saas_usage),
        CronTrigger(day=1, hour=0, minute=0),
        id="reset_saas_usage",
        name="Monthly SaaS usage counter reset",
        replace_existing=True,
    )

    logger.info(
        "[SCHEDULER] Configured %d jobs: content@%dh, outreach@%dh, usage-reset@1st-of-month",
        3,
        settings.content_generation_hour,
        settings.outreach_hour,
    )


def start_scheduler() -> None:
    if settings.scheduler_enabled:
        configure_scheduler()
        scheduler.start()
        logger.info("[SCHEDULER] Started")
    else:
        logger.info("[SCHEDULER] Disabled by config")


def shutdown_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("[SCHEDULER] Shut down")
