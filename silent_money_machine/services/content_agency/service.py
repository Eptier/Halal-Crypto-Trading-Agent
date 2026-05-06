"""Content Agency business logic — generate and deliver content for clients."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from silent_money_machine.core.database import Client, ContentPiece
from silent_money_machine.gpt_engine.content import (
    generate_blog_post,
    generate_newsletter,
    generate_seo_meta,
    generate_social_batch,
)

logger = logging.getLogger(__name__)


async def create_client(session: AsyncSession, data: dict[str, Any]) -> Client:
    client = Client(**data)
    session.add(client)
    await session.commit()
    await session.refresh(client)
    logger.info("Created client id=%d email=%s", client.id, client.email)
    return client


async def list_active_clients(session: AsyncSession) -> list[Client]:
    result = await session.execute(select(Client).where(Client.status == "active"))
    return list(result.scalars().all())


async def get_client(session: AsyncSession, client_id: int) -> Client | None:
    return await session.get(Client, client_id)


async def generate_content_for_client(
    session: AsyncSession,
    client: Client,
    content_type: str = "blog",
    topic: str = "",
    keywords: str = "",
) -> ContentPiece:
    """Generate a single content piece for a given client."""
    niche = client.niche or "general"
    topic = topic or f"Latest trends in {niche}"
    keywords = keywords or niche

    if content_type == "blog":
        resp = await generate_blog_post(topic=topic, keywords=keywords, niche=niche)
        title = topic
        body = resp.text
    elif content_type == "social":
        posts, resp = await generate_social_batch(niche=niche, platform="twitter", themes=topic)
        title = f"Social batch: {topic}"
        body = str(posts)
    elif content_type == "newsletter":
        data, resp = await generate_newsletter(
            topic=topic, niche=niche, audience="subscribers", key_points=keywords
        )
        title = data.get("subject", topic)
        body = data.get("body", resp.text)
    else:
        resp = await generate_blog_post(topic=topic, keywords=keywords, niche=niche)
        title = topic
        body = resp.text

    meta_data, _meta_resp = await generate_seo_meta(
        title=title, summary=body[:300], keywords=keywords
    )

    piece = ContentPiece(
        client_id=client.id,
        content_type=content_type,
        title=title,
        body=body,
        meta_description=meta_data.get("meta_description", ""),
        keywords=keywords,
        status="draft",
        tokens_used=resp.total_tokens,
        cost_usd=str(resp.cost_usd),
    )
    session.add(piece)
    await session.commit()
    await session.refresh(piece)
    logger.info(
        "Generated content id=%d type=%s client=%d tokens=%d",
        piece.id,
        content_type,
        client.id,
        resp.total_tokens,
    )
    return piece


async def batch_generate_for_all_clients(session: AsyncSession) -> list[ContentPiece]:
    """Scheduled job: generate content for every active client."""
    clients = await list_active_clients(session)
    pieces: list[ContentPiece] = []
    for client in clients:
        try:
            piece = await generate_content_for_client(session, client)
            pieces.append(piece)
        except Exception:
            logger.exception("Failed to generate content for client id=%d", client.id)
    return pieces


async def list_content(
    session: AsyncSession, client_id: int | None = None, limit: int = 50
) -> list[ContentPiece]:
    stmt = select(ContentPiece).order_by(ContentPiece.id.desc()).limit(limit)
    if client_id:
        stmt = stmt.where(ContentPiece.client_id == client_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())
