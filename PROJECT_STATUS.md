# PROJECT STATUS

## Project
AI Client Acquisition Agent

## Current Phase
PHASE 1 — FOUNDATION + LEAD HUNTER

(Phase 1 conceptually contains the former "Phase 0" foundation work; they
are tracked together. See Permanent Rules & Architecture → Development
Sequence, and docs/PHASE_1_SPECIFICATION.md for the definitive scope.)

## Overall Status
PHASE 1 FEATURE-COMPLETE PENDING REVIEW — foundation, data layer, scoring,
discovery providers, SSRF-safe research, API and CLI are implemented and
tested. Open items are listed under "Not Started / Open" below.

Correction (2026-11-10): earlier notes claimed the Lead Hunter layer was
complete before it existed. This file reflects the repository.

## Repository
https://github.com/Muaz-Ibn-Kamal/ai-client-acquisition-agent
Branches (not merged to main yet; review in order):
1. feat/phase1-data-layer-scoring — data model, scoring engine, companies/leads API
2. feat/phase1-discovery-research — discovery providers, fetcher, analyzer, research,
   /discover /research /score, CLI (stacked on 1)

## Completed (verified 2026-11-10: pytest 90 passed, ruff clean, mypy clean,
## alembic check clean, migration up/down/up OK on local PostgreSQL 16)

- Foundation: FastAPI skeleton, config, logging, async DB session, Alembic
- Data model + migration: companies, contacts (provenance, suppression-ready,
  retention fields), lead_sources, leads, opportunities (evidence-first,
  FACT/INFERENCE/UNKNOWN), website_analysis, lead_scores
- Domain normalization + company dedup (unique normalized domain)
- Deterministic scoring engine (6 components, 100 points, configurable weights,
  per-factor reasons, confidence; unknown = 0 points, never guessed)
- Signal derivation from research (only observable factors) + analyst overrides
- Discovery providers: manual, CSV import, Google Places (mocked tests only)
- SSRF-safe fetcher: public-IP checks on every hop, manual redirects (max 3),
  robots.txt, size cap, content-type check, timeouts
- Website analyzer: title/meta/headings/nav/tech/viewport/CTA/alt text/public
  contacts, each insight with evidence, source URL, confidence, label
- Research service: persists analysis, company-domain public contacts (with
  provenance) and opportunities; page content is treated as inert data
- API: /companies, /leads (filters, pagination, ranking), /discover,
  /research/{company_id}, /score/{lead_id}, /health. No outreach endpoints.
- CLI: discover, research, score, top-leads
- Live smoke test: CLI discover (CSV) -> research -> score against
  https://example.com worked end to end. It also exposed a gzip double-decode
  bug in the fetcher that mocked tests missed; fixed with a regression test.

## Not Started / Open (Phase 1)

- Google Places provider has NOT been run against the live API (needs a key)
- No LLM layer yet, so "AI structured-output validation" tests do not apply;
  Insight validation is tested instead
- No Playwright rendering (JS-only sites will look empty to the analyzer)
- Only the homepage is fetched (no multi-page crawl, no broken-link check)
- Basic CI not set up
- Tests require a reachable PostgreSQL server (they create `<db>_test`)

## Not Started (later phases)

- Phase 2 — Proposal Engine
- Phase 3 — Outreach Engine
- Phase 4 — WhatsApp AI
- Phase 5 — CRM Dashboard
- Phase 6 — Production Deployment

## Next Task

Review/merge both branches, add GitHub Actions CI, then (with approval) either
validate Google Places with a real key or begin Phase 2.

## Rules

- Do not skip phases.
- Do not implement future phases without approval.
- Do not implement anything on the Phase 1 non-goals list
  (docs/PHASE_1_SPECIFICATION.md §1.1) without explicit approval.
- Test every meaningful feature.
- Update this file after meaningful progress.
- Status Authority: if this file disagrees with the actual repository state,
  the repository is authoritative — correct this file and report the
  discrepancy to the user. Never blindly trust this file.

## Next Task

Create the GitHub repository, scaffold the project per
docs/PHASE_1_SPECIFICATION.md §3 (Architecture), and begin Phase 1
foundation implementation.
