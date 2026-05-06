"""Publicly exposed AI tool endpoints for SaaS subscribers."""

from __future__ import annotations

from typing import Any

from silent_money_machine.gpt_engine.content import (
    blog_writer_api,
    code_helper,
    compose_email,
    generate_resume,
)


async def tool_resume_writer(params: dict[str, str]) -> dict[str, Any]:
    resp = await generate_resume(
        name=params.get("name", ""),
        target_role=params.get("target_role", ""),
        experience=params.get("experience", ""),
        skills=params.get("skills", ""),
        education=params.get("education", ""),
    )
    return {"resume": resp.text, "tokens_used": resp.total_tokens, "cost": resp.cost_usd}


async def tool_email_writer(params: dict[str, str]) -> dict[str, Any]:
    data, resp = await compose_email(
        purpose=params.get("purpose", ""),
        recipient=params.get("recipient", ""),
        context=params.get("context", ""),
        tone=params.get("tone", "professional"),
        key_points=params.get("key_points", ""),
    )
    return {**data, "tokens_used": resp.total_tokens, "cost": resp.cost_usd}


async def tool_blog_writer(params: dict[str, str]) -> dict[str, Any]:
    resp = await blog_writer_api(
        topic=params.get("topic", ""),
        keywords=params.get("keywords", ""),
        tone=params.get("tone", "professional"),
        length=int(params.get("length", "1000")),
    )
    return {"blog": resp.text, "tokens_used": resp.total_tokens, "cost": resp.cost_usd}


async def tool_code_helper(params: dict[str, str]) -> dict[str, Any]:
    data, resp = await code_helper(
        language=params.get("language", "python"),
        task=params.get("task", ""),
        context=params.get("context", ""),
    )
    return {**data, "tokens_used": resp.total_tokens, "cost": resp.cost_usd}


TOOL_REGISTRY: dict[str, Any] = {
    "resume_writer": {
        "handler": tool_resume_writer,
        "description": "Generate a professional ATS-friendly resume",
        "params": ["name", "target_role", "experience", "skills", "education"],
    },
    "email_writer": {
        "handler": tool_email_writer,
        "description": "Compose professional emails for any purpose",
        "params": ["purpose", "recipient", "context", "tone", "key_points"],
    },
    "blog_writer": {
        "handler": tool_blog_writer,
        "description": "Write SEO-optimized blog posts on any topic",
        "params": ["topic", "keywords", "tone", "length"],
    },
    "code_helper": {
        "handler": tool_code_helper,
        "description": "Get coding solutions and explanations",
        "params": ["language", "task", "context"],
    },
}
