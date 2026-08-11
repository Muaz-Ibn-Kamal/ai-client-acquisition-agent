# AI Client Acquisition Agent

A backend system for discovering, researching, and scoring international
remote clients and projects — web development, redesign, landing pages,
UI/UX, branding, and related digital services — for a freelance business.

**Status:** Specification finalized. Implementation has not started yet.
See [PROJECT_STATUS.md](./PROJECT_STATUS.md) for the current state.

## What this is (eventually)

The long-term system discovers potential companies, researches their
websites, identifies opportunities, scores leads, generates personalized
proposals and cold emails, follows up with prospects, and qualifies them
over WhatsApp before handing high-value leads to a human. It's being built
in phases; each phase ships and gets tested before the next one starts.

## Current phase

**Phase 1 — Foundation + Lead Hunter.** Discovers companies from permitted
public sources, researches their websites for opportunities, and scores
leads with a transparent, deterministic scoring model. No outreach,
messaging, or proposal generation happens in this phase — see
[docs/PHASE_1_SPECIFICATION.md](./docs/PHASE_1_SPECIFICATION.md) for the
full, authoritative scope and explicit non-goals.

Later phases (not started): AI research & proposal engine, outreach engine,
WhatsApp AI agent, CRM dashboard, production deployment.

## Tech stack

Python 3.12+, uv, FastAPI, PostgreSQL, SQLAlchemy 2.x, Alembic, Pydantic v2,
httpx, BeautifulSoup4, Playwright (where needed), pytest, Ruff, MyPy.

## Getting started

Implementation hasn't started, so the steps below describe the intended
setup once Phase 1 lands — not a working system yet.

```bash
git clone <repo-url>
cd ai-client-acquisition-agent
uv sync
cp .env.example .env   # fill in DATABASE_URL, LLM_PROVIDER, LLM_API_KEY, etc.
docker compose up -d   # local PostgreSQL
uv run alembic upgrade head
uv run fastapi dev app/main.py
```

CLI (planned):

```bash
uv run python -m app.cli discover --query "SaaS startups"
uv run python -m app.cli research --company-id <UUID>
uv run python -m app.cli score --lead-id <UUID>
uv run python -m app.cli top-leads --min-score 80
```

## Documentation

- [docs/PHASE_1_SPECIFICATION.md](./docs/PHASE_1_SPECIFICATION.md) —
  definitive Phase 1 scope, architecture, database, API, CLI, scoring
  model, and non-goals.
- [CLAUDE.md](./CLAUDE.md) — instructions for Claude Code sessions working
  in this repo.
- [PROJECT_STATUS.md](./PROJECT_STATUS.md) — current progress, authoritative
  over any other status description.

## Principles

- Never skip phases; never implement a future phase without approval.
- Deterministic, transparent lead scoring — the LLM provides evidence, not
  the final score.
- Every research claim carries evidence, a source, and a confidence level,
  and is labeled fact, inference, or unknown.
- All external web content is treated as untrusted data, never as
  instructions.
- No fake integrations, no invented data — unknowns are marked as unknown.
