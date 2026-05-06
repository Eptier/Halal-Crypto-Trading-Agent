"""Prompt template library for all revenue streams."""

from __future__ import annotations

# ──────────────────────────────────────────────
#  Content Agency Prompts
# ──────────────────────────────────────────────

BLOG_POST = """Write a comprehensive, SEO-optimized blog post.

**Topic:** {topic}
**Target keywords:** {keywords}
**Niche:** {niche}
**Tone:** {tone}
**Word count:** {word_count} words

Requirements:
- Engaging introduction with a hook
- Use H2 and H3 subheadings
- Include actionable tips and examples
- Natural keyword placement (2-3% density)
- Compelling conclusion with a call to action
- Write in a conversational yet authoritative tone

Return the blog post in markdown format."""

SOCIAL_MEDIA_BATCH = """Create a batch of {count} social media posts for the following:

**Niche:** {niche}
**Platform:** {platform}
**Tone:** {tone}
**Key themes:** {themes}

For each post, provide:
1. The post text (within platform character limits)
2. Suggested hashtags (5-10 relevant ones)
3. Best posting time suggestion

Format as JSON array:
[{{"text": "...", "hashtags": ["..."], "best_time": "..."}}]"""

NEWSLETTER = """Write a professional email newsletter.

**Subject line topic:** {topic}
**Niche:** {niche}
**Audience:** {audience}
**Key points to cover:** {key_points}

Structure:
- Compelling subject line
- Personal greeting
- Main content (valuable insights, not salesy)
- One clear CTA
- Professional sign-off

Return as JSON: {{"subject": "...", "body": "..."}}"""

SEO_META = """Generate SEO metadata for the following content:

**Title:** {title}
**Content summary:** {summary}
**Target keywords:** {keywords}

Return as JSON:
{{"meta_title": "... (60 chars max)", "meta_description": "... (155 chars max)", "slug": "...", "focus_keyword": "..."}}"""

# ──────────────────────────────────────────────
#  Digital Product Prompts
# ──────────────────────────────────────────────

EBOOK_OUTLINE = """Create a detailed ebook outline.

**Topic:** {topic}
**Target audience:** {audience}
**Desired length:** {chapters} chapters
**Niche:** {niche}

Return as JSON:
{{
  "title": "...",
  "subtitle": "...",
  "description": "... (compelling sales copy, 2-3 sentences)",
  "chapters": [
    {{"number": 1, "title": "...", "sections": ["...", "..."], "key_points": ["...", "..."]}}
  ],
  "target_price_usd": "..."
}}"""

EBOOK_CHAPTER = """Write a complete ebook chapter.

**Book title:** {book_title}
**Chapter {chapter_number}: {chapter_title}**
**Sections to cover:** {sections}
**Key points:** {key_points}
**Tone:** Professional, actionable, and engaging
**Target length:** 2000-3000 words

Write the full chapter in markdown format with clear section headings."""

EMAIL_SEQUENCE = """Create a {length}-email automated email sequence.

**Goal:** {goal}
**Niche:** {niche}
**Target audience:** {audience}
**Product/Service:** {product}

For each email provide:
- Subject line
- Send timing (e.g., "Day 0", "Day 3")
- Email body
- CTA

Return as JSON array:
[{{"day": 0, "subject": "...", "body": "...", "cta": "..."}}]"""

LEAD_MAGNET = """Create a compelling lead magnet document.

**Topic:** {topic}
**Format:** {format} (checklist / cheat sheet / template / mini-guide)
**Niche:** {niche}
**Target audience:** {audience}

Requirements:
- Immediately actionable
- High perceived value
- Solves a specific pain point
- Professional formatting

Return the content in markdown format with a compelling title."""

# ──────────────────────────────────────────────
#  SaaS API Tool Prompts
# ──────────────────────────────────────────────

RESUME_WRITER = """Write a professional resume based on the following information:

**Name:** {name}
**Target role:** {target_role}
**Experience:** {experience}
**Skills:** {skills}
**Education:** {education}

Create an ATS-friendly resume in a clean, professional format.
Focus on quantifiable achievements and relevant skills.
Return in markdown format."""

EMAIL_COMPOSER = """Compose a professional email.

**Purpose:** {purpose}
**Recipient:** {recipient}
**Context:** {context}
**Tone:** {tone}
**Key points:** {key_points}

Return as JSON: {{"subject": "...", "body": "..."}}"""

CODE_HELPER = """Provide a solution for the following coding task:

**Language:** {language}
**Task:** {task}
**Context:** {context}

Provide:
1. Clean, well-commented code
2. Brief explanation
3. Any edge cases to consider

Return as JSON: {{"code": "...", "explanation": "...", "edge_cases": ["..."]}}"""

BLOG_WRITER_API = """Write a blog post based on the following brief:

**Topic:** {topic}
**Keywords:** {keywords}
**Tone:** {tone}
**Length:** {length} words

Return a well-structured blog post in markdown format with:
- SEO-optimized title
- Engaging introduction
- Organized subheadings
- Actionable conclusion"""

# ──────────────────────────────────────────────
#  Outreach Prompts
# ──────────────────────────────────────────────

COLD_EMAIL = """Write a personalized cold email for client acquisition.

**Recipient name:** {name}
**Recipient company:** {company}
**Their industry:** {industry}
**Pain point we solve:** {pain_point}
**Our service:** {service}
**Sender name:** {sender_name}

Requirements:
- Short (under 150 words)
- Personal, not templated-feeling
- Clear value proposition
- Soft CTA (no hard sell)
- Professional but warm

Return as JSON: {{"subject": "...", "body": "..."}}"""

FOLLOW_UP_EMAIL = """Write a follow-up email (attempt #{attempt_number}).

**Original email context:** {original_context}
**Recipient name:** {name}
**Days since last contact:** {days_since}

Requirements:
- Reference the previous email naturally
- Add new value (insight, case study, or tip)
- Keep it shorter than the original
- Gentle CTA

Return as JSON: {{"subject": "...", "body": "..."}}"""

LEAD_SCORING = """Analyze this lead and provide a quality score.

**Lead info:**
- Name: {name}
- Company: {company}
- Industry: {industry}
- Company size: {company_size}
- Source: {source}

**Our ideal customer:**
- Needs regular content creation
- Has marketing budget
- B2B or B2C with active online presence
- Company size 10-500 employees

Return as JSON:
{{"score": 0-100, "reasoning": "...", "recommended_approach": "...", "priority": "high|medium|low"}}"""
