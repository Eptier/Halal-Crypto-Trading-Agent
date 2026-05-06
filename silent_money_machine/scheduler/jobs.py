"""Scheduled job definitions — the 'silent' in Silent Money Machine."""

from __future__ import annotations

import logging

from silent_money_machine.core.database import ScheduledTask, async_session_factory

logger = logging.getLogger(__name__)


async def _record_task(task_type: str, description: str, result: str, error: str = "") -> None:
    async with async_session_factory() as session:
        task = ScheduledTask(
            task_type=task_type,
            description=description,
            status="completed" if not error else "failed",
            result=result,
            error=error,
        )
        session.add(task)
        await session.commit()


async def job_generate_content() -> None:
    """Daily: Generate content for all active content-agency clients."""
    from silent_money_machine.services.content_agency.service import (
        batch_generate_for_all_clients,
    )

    logger.info("[SCHEDULER] Running content generation job")
    try:
        async with async_session_factory() as session:
            pieces = await batch_generate_for_all_clients(session)
        await _record_task(
            "content_generation",
            "Daily content batch for all active clients",
            f"Generated {len(pieces)} pieces",
        )
    except Exception as exc:
        logger.exception("[SCHEDULER] Content generation failed")
        await _record_task("content_generation", "Daily content batch", "", str(exc))


async def job_daily_outreach() -> None:
    """Daily: Run outreach — cold emails + follow-ups."""
    from silent_money_machine.services.outreach.service import run_daily_outreach

    logger.info("[SCHEDULER] Running daily outreach job")
    try:
        async with async_session_factory() as session:
            stats = await run_daily_outreach(session)
        await _record_task(
            "daily_outreach",
            "Cold emails and follow-ups",
            str(stats),
        )
    except Exception as exc:
        logger.exception("[SCHEDULER] Daily outreach failed")
        await _record_task("daily_outreach", "Cold emails and follow-ups", "", str(exc))


async def job_reset_saas_usage() -> None:
    """Monthly: Reset SaaS API usage counters."""
    from silent_money_machine.services.saas_api.service import reset_monthly_usage

    logger.info("[SCHEDULER] Resetting monthly SaaS usage")
    try:
        async with async_session_factory() as session:
            count = await reset_monthly_usage(session)
        await _record_task(
            "reset_saas_usage",
            "Monthly usage counter reset",
            f"Reset {count} subscriptions",
        )
    except Exception as exc:
        logger.exception("[SCHEDULER] Usage reset failed")
        await _record_task("reset_saas_usage", "Monthly reset", "", str(exc))
