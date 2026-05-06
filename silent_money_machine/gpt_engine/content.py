"""High-level content generation strategies using the GPT client + prompt templates."""

from __future__ import annotations

import json
import logging
from typing import Any

from silent_money_machine.gpt_engine.client import GPTResponse, gpt_client
from silent_money_machine.gpt_engine.prompts import (
    BLOG_POST,
    BLOG_WRITER_API,
    CODE_HELPER,
    COLD_EMAIL,
    EBOOK_CHAPTER,
    EBOOK_OUTLINE,
    EMAIL_COMPOSER,
    EMAIL_SEQUENCE,
    FOLLOW_UP_EMAIL,
    LEAD_MAGNET,
    LEAD_SCORING,
    NEWSLETTER,
    RESUME_WRITER,
    SEO_META,
    SOCIAL_MEDIA_BATCH,
)

logger = logging.getLogger(__name__)


def _safe_json_parse(text: str) -> Any:
    """Attempt to parse JSON from GPT output, stripping markdown fences if present."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [ln for ln in lines if not ln.strip().startswith("```")]
        cleaned = "\n".join(lines)
    return json.loads(cleaned)


# ──────────────────────────────────────────────
#  Content Agency
# ──────────────────────────────────────────────


async def generate_blog_post(
    topic: str,
    keywords: str,
    niche: str,
    tone: str = "professional",
    word_count: int = 1500,
) -> GPTResponse:
    prompt = BLOG_POST.format(
        topic=topic, keywords=keywords, niche=niche, tone=tone, word_count=word_count
    )
    return await gpt_client.generate(prompt)


async def generate_social_batch(
    niche: str,
    platform: str,
    themes: str,
    tone: str = "engaging",
    count: int = 7,
) -> tuple[list[dict[str, Any]], GPTResponse]:
    prompt = SOCIAL_MEDIA_BATCH.format(
        niche=niche, platform=platform, themes=themes, tone=tone, count=count
    )
    resp = await gpt_client.generate_structured(prompt)
    posts = _safe_json_parse(resp.text)
    return posts, resp


async def generate_newsletter(
    topic: str, niche: str, audience: str, key_points: str
) -> tuple[dict[str, str], GPTResponse]:
    prompt = NEWSLETTER.format(
        topic=topic, niche=niche, audience=audience, key_points=key_points
    )
    resp = await gpt_client.generate_structured(prompt)
    data = _safe_json_parse(resp.text)
    return data, resp


async def generate_seo_meta(
    title: str, summary: str, keywords: str
) -> tuple[dict[str, str], GPTResponse]:
    prompt = SEO_META.format(title=title, summary=summary, keywords=keywords)
    resp = await gpt_client.generate_structured(prompt)
    data = _safe_json_parse(resp.text)
    return data, resp


# ──────────────────────────────────────────────
#  Digital Products
# ──────────────────────────────────────────────


async def generate_ebook_outline(
    topic: str, audience: str, niche: str, chapters: int = 8
) -> tuple[dict[str, Any], GPTResponse]:
    prompt = EBOOK_OUTLINE.format(
        topic=topic, audience=audience, niche=niche, chapters=chapters
    )
    resp = await gpt_client.generate_structured(prompt)
    outline = _safe_json_parse(resp.text)
    return outline, resp


async def generate_ebook_chapter(
    book_title: str,
    chapter_number: int,
    chapter_title: str,
    sections: str,
    key_points: str,
) -> GPTResponse:
    prompt = EBOOK_CHAPTER.format(
        book_title=book_title,
        chapter_number=chapter_number,
        chapter_title=chapter_title,
        sections=sections,
        key_points=key_points,
    )
    return await gpt_client.generate(prompt, max_tokens=4096)


async def generate_email_sequence(
    goal: str, niche: str, audience: str, product: str, length: int = 5
) -> tuple[list[dict[str, Any]], GPTResponse]:
    prompt = EMAIL_SEQUENCE.format(
        goal=goal, niche=niche, audience=audience, product=product, length=length
    )
    resp = await gpt_client.generate_structured(prompt)
    sequence = _safe_json_parse(resp.text)
    return sequence, resp


async def generate_lead_magnet(
    topic: str,
    magnet_format: str,
    niche: str,
    audience: str,
) -> GPTResponse:
    prompt = LEAD_MAGNET.format(
        topic=topic, format=magnet_format, niche=niche, audience=audience
    )
    return await gpt_client.generate(prompt)


# ──────────────────────────────────────────────
#  SaaS API Tools
# ──────────────────────────────────────────────


async def generate_resume(
    name: str, target_role: str, experience: str, skills: str, education: str
) -> GPTResponse:
    prompt = RESUME_WRITER.format(
        name=name,
        target_role=target_role,
        experience=experience,
        skills=skills,
        education=education,
    )
    return await gpt_client.generate(prompt)


async def compose_email(
    purpose: str, recipient: str, context: str, tone: str, key_points: str
) -> tuple[dict[str, str], GPTResponse]:
    prompt = EMAIL_COMPOSER.format(
        purpose=purpose,
        recipient=recipient,
        context=context,
        tone=tone,
        key_points=key_points,
    )
    resp = await gpt_client.generate_structured(prompt)
    data = _safe_json_parse(resp.text)
    return data, resp


async def code_helper(
    language: str, task: str, context: str = ""
) -> tuple[dict[str, Any], GPTResponse]:
    prompt = CODE_HELPER.format(language=language, task=task, context=context)
    resp = await gpt_client.generate_structured(prompt)
    data = _safe_json_parse(resp.text)
    return data, resp


async def blog_writer_api(
    topic: str, keywords: str = "", tone: str = "professional", length: int = 1000
) -> GPTResponse:
    prompt = BLOG_WRITER_API.format(
        topic=topic, keywords=keywords, tone=tone, length=length
    )
    return await gpt_client.generate(prompt)


# ──────────────────────────────────────────────
#  Outreach
# ──────────────────────────────────────────────


async def generate_cold_email(
    name: str,
    company: str,
    industry: str,
    pain_point: str,
    service: str,
    sender_name: str,
) -> tuple[dict[str, str], GPTResponse]:
    prompt = COLD_EMAIL.format(
        name=name,
        company=company,
        industry=industry,
        pain_point=pain_point,
        service=service,
        sender_name=sender_name,
    )
    resp = await gpt_client.generate_structured(prompt)
    data = _safe_json_parse(resp.text)
    return data, resp


async def generate_follow_up(
    name: str, original_context: str, days_since: int, attempt_number: int
) -> tuple[dict[str, str], GPTResponse]:
    prompt = FOLLOW_UP_EMAIL.format(
        name=name,
        original_context=original_context,
        days_since=days_since,
        attempt_number=attempt_number,
    )
    resp = await gpt_client.generate_structured(prompt)
    data = _safe_json_parse(resp.text)
    return data, resp


async def score_lead(
    name: str, company: str, industry: str, company_size: str, source: str
) -> tuple[dict[str, Any], GPTResponse]:
    prompt = LEAD_SCORING.format(
        name=name,
        company=company,
        industry=industry,
        company_size=company_size,
        source=source,
    )
    resp = await gpt_client.generate_structured(prompt)
    data = _safe_json_parse(resp.text)
    return data, resp
