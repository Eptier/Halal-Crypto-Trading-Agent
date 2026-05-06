"""Digital Product Factory — auto-generate ebooks, lead magnets, email sequences."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from silent_money_machine.core.database import DigitalProduct
from silent_money_machine.gpt_engine.content import (
    generate_ebook_chapter,
    generate_ebook_outline,
    generate_email_sequence,
    generate_lead_magnet,
)

logger = logging.getLogger(__name__)


async def create_ebook(
    session: AsyncSession,
    topic: str,
    audience: str,
    niche: str,
    chapters: int = 8,
    price: str = "19.99",
) -> DigitalProduct:
    """Generate a complete ebook: outline first, then each chapter."""
    outline, outline_resp = await generate_ebook_outline(topic, audience, niche, chapters)

    full_content_parts: list[str] = [
        f"# {outline.get('title', topic)}\n\n"
        f"*{outline.get('subtitle', '')}*\n\n"
        f"{outline.get('description', '')}\n\n---\n\n"
    ]

    total_tokens = outline_resp.total_tokens
    total_cost = outline_resp.cost_usd

    for ch in outline.get("chapters", []):
        ch_resp = await generate_ebook_chapter(
            book_title=outline.get("title", topic),
            chapter_number=ch.get("number", 0),
            chapter_title=ch.get("title", ""),
            sections=", ".join(ch.get("sections", [])),
            key_points=", ".join(ch.get("key_points", [])),
        )
        full_content_parts.append(ch_resp.text + "\n\n---\n\n")
        total_tokens += ch_resp.total_tokens
        total_cost += ch_resp.cost_usd

    full_content = "".join(full_content_parts)

    product = DigitalProduct(
        product_type="ebook",
        title=outline.get("title", topic),
        description=outline.get("description", ""),
        niche=niche,
        content=full_content,
        price_usd=price,
        status="draft",
    )
    session.add(product)
    await session.commit()
    await session.refresh(product)

    logger.info(
        "Created ebook id=%d title=%s tokens=%d cost=$%.4f",
        product.id,
        product.title,
        total_tokens,
        total_cost,
    )
    return product


async def create_lead_magnet_product(
    session: AsyncSession,
    topic: str,
    magnet_format: str,
    niche: str,
    audience: str,
    price: str = "0.00",
) -> DigitalProduct:
    resp = await generate_lead_magnet(topic, magnet_format, niche, audience)
    product = DigitalProduct(
        product_type="lead_magnet",
        title=f"{magnet_format.title()}: {topic}",
        description=f"Free {magnet_format} for {audience}",
        niche=niche,
        content=resp.text,
        price_usd=price,
        status="draft",
    )
    session.add(product)
    await session.commit()
    await session.refresh(product)
    return product


async def create_email_sequence_product(
    session: AsyncSession,
    goal: str,
    niche: str,
    audience: str,
    product_name: str,
    length: int = 5,
    price: str = "29.99",
) -> DigitalProduct:
    sequence, _resp = await generate_email_sequence(goal, niche, audience, product_name, length)
    product = DigitalProduct(
        product_type="email_sequence",
        title=f"Email Sequence: {goal}",
        description=f"{length}-email sequence for {audience}",
        niche=niche,
        content=str(sequence),
        price_usd=price,
        status="draft",
    )
    session.add(product)
    await session.commit()
    await session.refresh(product)
    return product


async def list_products(
    session: AsyncSession,
    product_type: str | None = None,
    status: str | None = None,
    limit: int = 50,
) -> list[DigitalProduct]:
    stmt = select(DigitalProduct).order_by(DigitalProduct.id.desc()).limit(limit)
    if product_type:
        stmt = stmt.where(DigitalProduct.product_type == product_type)
    if status:
        stmt = stmt.where(DigitalProduct.status == status)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_product(session: AsyncSession, product_id: int) -> DigitalProduct | None:
    return await session.get(DigitalProduct, product_id)


async def publish_product(session: AsyncSession, product_id: int) -> DigitalProduct | None:
    product = await session.get(DigitalProduct, product_id)
    if product:
        product.status = "published"
        await session.commit()
        await session.refresh(product)
    return product
