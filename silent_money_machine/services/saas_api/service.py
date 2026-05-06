"""SaaS API service — manage subscriptions and track usage of AI tools."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from silent_money_machine.core.database import SaasSubscription
from silent_money_machine.core.security import generate_api_key

logger = logging.getLogger(__name__)


async def create_subscription(
    session: AsyncSession,
    email: str,
    name: str = "",
    plan: str = "basic",
) -> SaasSubscription:
    api_key = generate_api_key()
    quotas = {"basic": 1000, "pro": 5000, "enterprise": 20000}
    sub = SaasSubscription(
        email=email,
        name=name,
        api_key=api_key,
        plan=plan,
        monthly_quota=quotas.get(plan, 1000),
    )
    session.add(sub)
    await session.commit()
    await session.refresh(sub)
    logger.info("Created SaaS subscription id=%d plan=%s", sub.id, plan)
    return sub


async def get_subscription_by_key(
    session: AsyncSession, api_key: str
) -> SaasSubscription | None:
    result = await session.execute(
        select(SaasSubscription).where(SaasSubscription.api_key == api_key)
    )
    return result.scalar_one_or_none()


async def check_and_increment_usage(
    session: AsyncSession, sub: SaasSubscription, tokens: int = 1
) -> bool:
    """Return True if usage is within quota, increment counter."""
    if sub.used_this_month + tokens > sub.monthly_quota:
        return False
    sub.used_this_month += tokens
    await session.commit()
    return True


async def list_subscriptions(session: AsyncSession) -> list[SaasSubscription]:
    result = await session.execute(
        select(SaasSubscription).order_by(SaasSubscription.id.desc())
    )
    return list(result.scalars().all())


async def reset_monthly_usage(session: AsyncSession) -> int:
    """Called monthly by scheduler to reset all usage counters."""
    subs = await list_subscriptions(session)
    count = 0
    for sub in subs:
        if sub.status == "active":
            sub.used_this_month = 0
            count += 1
    await session.commit()
    logger.info("Reset monthly usage for %d subscriptions", count)
    return count
