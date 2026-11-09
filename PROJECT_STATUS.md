# PROJECT STATUS

## Project
AI Client Acquisition Agent

## Current Phase
PHASE 1 — FOUNDATION + LEAD HUNTER

(Phase 1 conceptually contains the former "Phase 0" foundation work; they
are tracked together. See Permanent Rules & Architecture → Development
Sequence, and docs/PHASE_1_SPECIFICATION.md for the definitive scope.)

## Overall Status
PHASE 1 IN PROGRESS — Foundation done; Lead Hunter data layer, scoring engine and
companies/leads API done and tested. Discovery providers, website research,
/discover /research /score endpoints and the CLI are NOT implemented.

Correction (2026-11-10): earlier notes claimed the Lead Hunter layer was
complete. The repository only contained the foundation (health endpoint, DB
session, empty initial migration), so this file now reflects the repo.

## Repository
https://github.com/Muaz-Ibn-Kamal/ai-client-acquisition-agent
Work branch: feat/phase1-data-layer-scoring (not merged to main yet).

## Completed (verified)

- Foundation: FastAPI skeleton, config, logging, async DB session, Alembic
- Data model + migration 64a3e2e8c928: companies, contacts (with provenance,
  suppression-ready and retention fields), lead_sources, leads, opportunities
  (evidence-first, FACT/INFERENCE/UNKNOWN), website_analysis, lead_scores
- Domain normalization + company dedup (unique normalized domain)
- Deterministic scoring engine (6 components, 100 points, configurable
  weights, per-factor reasons, confidence, unknown = 0 points)
- API: POST/GET /companies, GET /companies/{id}, POST/GET /leads,
  GET /leads/{id} with pagination and filters (min_score, country, service,
  status), ranking by latest score
- Verification run 2026-11-10 against local PostgreSQL 16: pytest 50 passed,
  ruff clean, mypy clean, `alembic upgrade head` / `downgrade base` / `upgrade
  head` round trip OK, `alembic check` reports no drift

## In Progress

None.

## Not Started (Phase 1)

- Discovery provider architecture and specific sources (major decision —
  needs approval before implementation)
- Website retrieval/parsing, tech detection, SSRF-safe fetcher (Step: research)
- Opportunity detection from research; AI structured-output validation
- POST /discover, POST /research/{company_id}, POST /score/{lead_id}
- CLI (discover, research, score, top-leads)
- Basic CI

## Not Started (later phases)

- Phase 2 — Proposal Engine
- Phase 3 — Outreach Engine
- Phase 4 — WhatsApp AI
- Phase 5 — CRM Dashboard
- Phase 6 — Production Deployment

## Known Issues / Notes

- Tests need a reachable PostgreSQL server (they create `<db>_test`).
- Scoring signals are supplied by callers; nothing computes them from research yet.

## Next Task

Decide the lead discovery provider(s), then implement the SSRF-safe website
fetcher and research service.

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
