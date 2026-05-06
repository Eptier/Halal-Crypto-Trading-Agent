"""Revenue and performance metric calculations."""

from __future__ import annotations

import datetime as dt
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from silent_money_machine.core.database import (
    Client,
    ContentPiece,
    DigitalProduct,
    Lead,
    RevenueRecord,
    SaasSubscription,
    ScheduledTask,
)


async def get_overview(session: AsyncSession) -> dict[str, Any]:
    """High-level dashboard stats."""
    clients = (await session.execute(select(func.count(Client.id)))).scalar() or 0
    active_clients = (
        await session.execute(
            select(func.count(Client.id)).where(Client.status == "active")
        )
    ).scalar() or 0

    content_count = (
        await session.execute(select(func.count(ContentPiece.id)))
    ).scalar() or 0

    products = (
        await session.execute(select(func.count(DigitalProduct.id)))
    ).scalar() or 0
    published_products = (
        await session.execute(
            select(func.count(DigitalProduct.id)).where(DigitalProduct.status == "published")
        )
    ).scalar() or 0

    subs = (
        await session.execute(
            select(func.count(SaasSubscription.id)).where(SaasSubscription.status == "active")
        )
    ).scalar() or 0

    leads = (await session.execute(select(func.count(Lead.id)))).scalar() or 0
    hot_leads = (
        await session.execute(
            select(func.count(Lead.id)).where(Lead.score >= 70)
        )
    ).scalar() or 0

    return {
        "clients": {"total": clients, "active": active_clients},
        "content_pieces": content_count,
        "products": {"total": products, "published": published_products},
        "saas_subscribers": subs,
        "leads": {"total": leads, "hot": hot_leads},
    }


async def get_revenue_summary(session: AsyncSession, month: str | None = None) -> dict[str, Any]:
    """Revenue by stream for a given month (defaults to current)."""
    if not month:
        month = dt.date.today().strftime("%Y-%m")

    result = await session.execute(
        select(RevenueRecord).where(RevenueRecord.month == month)
    )
    records = result.scalars().all()

    streams: dict[str, dict[str, Any]] = {}
    total = 0.0
    for rec in records:
        amount = float(rec.amount_usd)
        streams[rec.stream] = {
            "amount_usd": rec.amount_usd,
            "transactions": rec.transactions,
        }
        total += amount

    return {"month": month, "total_usd": f"{total:.2f}", "streams": streams}


async def get_scheduler_history(session: AsyncSession, limit: int = 20) -> list[dict[str, Any]]:
    result = await session.execute(
        select(ScheduledTask).order_by(ScheduledTask.id.desc()).limit(limit)
    )
    tasks = result.scalars().all()
    return [
        {
            "id": t.id,
            "type": t.task_type,
            "status": t.status,
            "result": t.result[:200] if t.result else "",
            "error": t.error[:200] if t.error else "",
            "created_at": str(t.created_at),
        }
        for t in tasks
    ]


async def record_revenue(
    session: AsyncSession,
    stream: str,
    amount_usd: str,
    transactions: int = 1,
    month: str | None = None,
) -> RevenueRecord:
    if not month:
        month = dt.date.today().strftime("%Y-%m")

    result = await session.execute(
        select(RevenueRecord).where(
            RevenueRecord.month == month, RevenueRecord.stream == stream
        )
    )
    record = result.scalar_one_or_none()

    if record:
        record.amount_usd = f"{float(record.amount_usd) + float(amount_usd):.2f}"
        record.transactions += transactions
    else:
        record = RevenueRecord(
            month=month,
            stream=stream,
            amount_usd=amount_usd,
            transactions=transactions,
        )
        session.add(record)

    await session.commit()
    await session.refresh(record)
    return record
