"""Database engine, session factory, and base model for SQLAlchemy async ORM."""

from __future__ import annotations

import datetime as dt
from collections.abc import AsyncGenerator

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from silent_money_machine.core.config import settings

engine = create_async_engine(settings.database_url, echo=settings.app_debug)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Shared base for all ORM models."""

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ──────────────────────────────────────────────
#  Domain Models
# ──────────────────────────────────────────────


class Client(Base):
    """A content-agency client who pays for automated content."""

    __tablename__ = "clients"

    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(200), unique=True)
    company: Mapped[str] = mapped_column(String(200), default="")
    niche: Mapped[str] = mapped_column(String(200), default="")
    plan: Mapped[str] = mapped_column(String(50), default="basic")  # basic | pro
    stripe_customer_id: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[str] = mapped_column(String(50), default="active")  # active | paused | churned
    delivery_method: Mapped[str] = mapped_column(String(50), default="email")  # email | webhook
    webhook_url: Mapped[str] = mapped_column(String(500), default="")
    content_frequency: Mapped[str] = mapped_column(String(50), default="weekly")
    notes: Mapped[str] = mapped_column(Text, default="")


class ContentPiece(Base):
    """A generated content piece for a client."""

    __tablename__ = "content_pieces"

    client_id: Mapped[int] = mapped_column(Integer, index=True)
    content_type: Mapped[str] = mapped_column(String(50))  # blog | social | newsletter | seo
    title: Mapped[str] = mapped_column(String(500))
    body: Mapped[str] = mapped_column(Text)
    meta_description: Mapped[str] = mapped_column(String(500), default="")
    keywords: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(50), default="draft")  # draft | delivered | failed
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[str] = mapped_column(String(20), default="0.00")


class DigitalProduct(Base):
    """An auto-generated digital product (ebook, lead magnet, course outline, etc.)."""

    __tablename__ = "digital_products"

    product_type: Mapped[str] = mapped_column(String(50))  # ebook | lead_magnet | email_sequence | course_outline
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text, default="")
    niche: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    price_usd: Mapped[str] = mapped_column(String(20), default="19.99")
    platform: Mapped[str] = mapped_column(String(100), default="gumroad")
    platform_url: Mapped[str] = mapped_column(String(500), default="")
    sales_count: Mapped[int] = mapped_column(Integer, default=0)
    revenue_usd: Mapped[str] = mapped_column(String(20), default="0.00")
    status: Mapped[str] = mapped_column(String(50), default="draft")  # draft | published | archived


class SaasSubscription(Base):
    """A subscriber to the AI Micro-SaaS API."""

    __tablename__ = "saas_subscriptions"

    email: Mapped[str] = mapped_column(String(200), unique=True)
    name: Mapped[str] = mapped_column(String(200), default="")
    api_key: Mapped[str] = mapped_column(String(200), unique=True)
    plan: Mapped[str] = mapped_column(String(50), default="basic")  # basic | pro | enterprise
    stripe_subscription_id: Mapped[str] = mapped_column(String(200), default="")
    monthly_quota: Mapped[int] = mapped_column(Integer, default=1000)
    used_this_month: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(50), default="active")


class Lead(Base):
    """A prospective client discovered by the outreach engine."""

    __tablename__ = "leads"

    email: Mapped[str] = mapped_column(String(200), unique=True)
    name: Mapped[str] = mapped_column(String(200), default="")
    company: Mapped[str] = mapped_column(String(200), default="")
    source: Mapped[str] = mapped_column(String(100), default="")  # linkedin | scrape | referral
    score: Mapped[int] = mapped_column(Integer, default=0)  # 0-100 lead score
    outreach_stage: Mapped[str] = mapped_column(
        String(50), default="new"
    )  # new | contacted | follow_up_1 | follow_up_2 | converted | dead
    last_contacted_at: Mapped[str] = mapped_column(String(50), default="")
    notes: Mapped[str] = mapped_column(Text, default="")


class ScheduledTask(Base):
    """Record of a scheduled automation task execution."""

    __tablename__ = "scheduled_tasks"

    task_type: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending | running | completed | failed
    result: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str] = mapped_column(Text, default="")


class RevenueRecord(Base):
    """Monthly revenue tracking per stream."""

    __tablename__ = "revenue_records"

    month: Mapped[str] = mapped_column(String(10))  # YYYY-MM
    stream: Mapped[str] = mapped_column(String(50))  # content_agency | product_factory | saas_api
    amount_usd: Mapped[str] = mapped_column(String(20), default="0.00")
    transactions: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str] = mapped_column(Text, default="")
