# Silent Money Machine

AI-powered backend automation system for generating passive income through GPT and silent automation. **Halal compliant** — no interest, gambling, or speculation.

## Revenue Streams

| Stream | Target | How |
|--------|--------|-----|
| **AI Content Agency** | $6,000-8,000/mo | Auto-generate SEO blogs, social posts, newsletters for clients |
| **Digital Product Factory** | $4,000-5,000/mo | Auto-create ebooks, lead magnets, email sequences |
| **AI Micro-SaaS API** | $3,000-4,000/mo | GPT-powered tools (resume writer, email composer, code helper) |
| **Automated Outreach** | Feeds other streams | Cold email, lead scoring, follow-up automation |

## Tech Stack

- **Backend:** FastAPI + SQLAlchemy (async)
- **AI:** OpenAI GPT API (gpt-4o-mini default)
- **Payments:** Stripe
- **Scheduler:** APScheduler (cron-based silent automation)
- **Database:** SQLite (dev) / PostgreSQL (prod)
- **Email:** Resend / SMTP

## Quick Start

```bash
# Install dependencies
uv sync --extra dev

# Copy environment config
cp .env.example .env
# Edit .env with your API keys (OpenAI, Stripe, etc.)

# Run the server
uv run python -m silent_money_machine

# Or with uvicorn directly
uv run uvicorn silent_money_machine.main:app --reload
```

API docs available at: `http://localhost:8000/docs`

## API Overview

### Content Agency (`/content-agency`)
- `POST /content-agency/clients` — Onboard a new content client
- `GET /content-agency/clients` — List active clients
- `POST /content-agency/clients/{id}/generate` — Generate content for a client
- `POST /content-agency/generate-all` — Batch generate for all clients
- `GET /content-agency/content` — List generated content

### Digital Products (`/products`)
- `POST /products/ebook` — Generate a complete ebook
- `POST /products/lead-magnet` — Generate a lead magnet
- `POST /products/email-sequence` — Generate an email sequence
- `GET /products/` — List all products
- `POST /products/{id}/publish` — Publish a product

### SaaS API (`/saas`)
- `GET /saas/tools` — List available AI tools (public)
- `POST /saas/tools/run` — Run a tool (subscriber key required)
- `POST /saas/subscriptions` — Create subscription (admin)
- `GET /saas/subscriptions` — List subscriptions (admin)

### Outreach (`/outreach`)
- `POST /outreach/leads` — Add a lead with auto-scoring
- `POST /outreach/leads/bulk` — Bulk add leads
- `GET /outreach/leads` — List leads by score/stage
- `POST /outreach/leads/{id}/contact` — Send cold email
- `POST /outreach/leads/{id}/follow-up` — Send follow-up
- `POST /outreach/run-daily` — Trigger daily outreach cycle

### Billing (`/billing`)
- `POST /billing/customers` — Create Stripe customer
- `POST /billing/checkout` — Create checkout session
- `POST /billing/pay` — One-time payment
- `POST /billing/webhook` — Stripe webhook handler

### Dashboard (`/dashboard`)
- `GET /dashboard/overview` — System metrics
- `GET /dashboard/revenue` — Revenue by month/stream
- `POST /dashboard/revenue` — Record revenue
- `GET /dashboard/scheduler` — Scheduled job history

## Automated Schedules

The scheduler runs these jobs silently:

| Job | Schedule | What it does |
|-----|----------|-------------|
| Content Generation | Daily 6:00 AM | Generates content for all active clients |
| Outreach | Daily 9:00 AM | Sends cold emails and follow-ups |
| Usage Reset | 1st of month | Resets SaaS API monthly usage quotas |

## Testing

```bash
uv run pytest
uv run ruff check silent_money_machine tests
uv run mypy silent_money_machine
```

## Project Structure

```
silent_money_machine/
├── core/           # Config, database models, security
├── gpt_engine/     # OpenAI client, prompts, content generation
├── services/
│   ├── content_agency/  # Stream 1: Auto content for clients
│   ├── product_factory/ # Stream 2: Digital product generation
│   ├── saas_api/        # Stream 3: AI tools as API
│   └── outreach/        # Stream 4: Client acquisition
├── billing/        # Stripe integration
├── scheduler/      # APScheduler cron jobs
├── dashboard/      # Analytics & monitoring
└── main.py         # FastAPI app entry
```

## License

Private — All rights reserved.
