"""Automated outreach engine — lead management, cold emails, follow-ups."""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from silent_money_machine.core.config import settings
from silent_money_machine.core.database import Lead
from silent_money_machine.gpt_engine.content import (
    generate_cold_email,
    generate_follow_up,
    score_lead,
)

logger = logging.getLogger(__name__)


_LEAD_COLUMNS = {c.key for c in Lead.__table__.columns if c.key != "id"}


async def add_lead(session: AsyncSession, data: dict[str, Any]) -> Lead:
    filtered = {k: v for k, v in data.items() if k in _LEAD_COLUMNS}
    lead = Lead(**filtered)
    session.add(lead)
    await session.commit()
    await session.refresh(lead)
    return lead


async def add_and_score_lead(
    session: AsyncSession,
    name: str,
    email: str,
    company: str,
    industry: str,
    company_size: str = "unknown",
    source: str = "manual",
) -> Lead:
    """Add a lead and auto-score it with GPT."""
    score_data, _resp = await score_lead(name, company, industry, company_size, source)
    lead = Lead(
        name=name,
        email=email,
        company=company,
        source=source,
        score=score_data.get("score", 50),
        notes=score_data.get("reasoning", ""),
    )
    session.add(lead)
    await session.commit()
    await session.refresh(lead)
    logger.info("Added lead id=%d score=%d", lead.id, lead.score)
    return lead


async def list_leads(
    session: AsyncSession,
    stage: str | None = None,
    min_score: int = 0,
    limit: int = 100,
) -> list[Lead]:
    stmt = (
        select(Lead)
        .where(Lead.score >= min_score)
        .order_by(Lead.score.desc())
        .limit(limit)
    )
    if stage:
        stmt = stmt.where(Lead.outreach_stage == stage)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def send_cold_outreach(
    session: AsyncSession,
    lead: Lead,
    service: str = "AI-powered content automation",
    pain_point: str = "spending too much time creating marketing content",
    sender_name: str = "The Team",
) -> dict[str, str]:
    """Generate and 'send' a cold email to a lead (logs it; real SMTP is pluggable)."""
    email_data, _resp = await generate_cold_email(
        name=lead.name,
        company=lead.company,
        industry=lead.notes[:100] if lead.notes else "technology",
        pain_point=pain_point,
        service=service,
        sender_name=sender_name,
    )
    lead.outreach_stage = "contacted"
    lead.last_contacted_at = dt.datetime.now(dt.UTC).isoformat()
    await session.commit()
    logger.info("Sent cold email to lead id=%d email=%s", lead.id, lead.email)
    return email_data


async def send_follow_up(
    session: AsyncSession,
    lead: Lead,
    attempt: int = 1,
) -> dict[str, str]:
    days_since = 3 if attempt == 1 else 7
    email_data, _resp = await generate_follow_up(
        name=lead.name,
        original_context=f"Outreach about AI content services to {lead.company}",
        days_since=days_since,
        attempt_number=attempt,
    )
    stage_map = {1: "follow_up_1", 2: "follow_up_2", 3: "follow_up_3"}
    lead.outreach_stage = stage_map.get(attempt, f"follow_up_{attempt}")
    lead.last_contacted_at = dt.datetime.now(dt.UTC).isoformat()
    await session.commit()
    logger.info("Sent follow-up #%d to lead id=%d", attempt, lead.id)
    return email_data


async def run_daily_outreach(session: AsyncSession) -> dict[str, int]:
    """Scheduled job: send cold emails to new leads, follow up on existing ones."""
    limit = settings.daily_outreach_limit
    stats = {"cold_sent": 0, "follow_ups_sent": 0}

    new_leads = await list_leads(session, stage="new", min_score=40, limit=limit // 2)
    for lead in new_leads:
        try:
            await send_cold_outreach(session, lead)
            stats["cold_sent"] += 1
        except Exception:
            logger.exception("Failed cold outreach to lead id=%d", lead.id)

    contacted_leads = await list_leads(session, stage="contacted", limit=limit // 2)
    for lead in contacted_leads:
        try:
            await send_follow_up(session, lead, attempt=1)
            stats["follow_ups_sent"] += 1
        except Exception:
            logger.exception("Failed follow-up for lead id=%d", lead.id)

    logger.info("Daily outreach: %s", stats)
    return stats
