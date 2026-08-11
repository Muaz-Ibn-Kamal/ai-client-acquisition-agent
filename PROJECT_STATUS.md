# PROJECT STATUS

## Project
AI Client Acquisition Agent

## Current Phase
PHASE 1 — FOUNDATION + LEAD HUNTER

(Phase 1 conceptually contains the former "Phase 0" foundation work; they
are tracked together. See Permanent Rules & Architecture → Development
Sequence, and docs/PHASE_1_SPECIFICATION.md for the definitive scope.)

## Overall Status
SPECIFICATION FINALIZED — IMPLEMENTATION NOT STARTED

## Repository
Not yet created. Per project decision, source code will live in a local Git
repository connected to GitHub, worked on primarily through Claude Code.
This file becomes authoritative once that repository exists (see "Status
Authority" under Rules, below). Until then, this is the working record,
mirrored in Project Knowledge.

## Completed

- Project created
- Claude Project configured
- Master project instructions created
- Setup audit performed (contradictions, gaps, and risks identified)
- Project constitution finalized (Permanent Rules & Architecture updated to
  resolve every audit finding)
- Phase 1 specification finalized (docs/PHASE_1_SPECIFICATION.md — scope,
  tech stack, architecture, database, API, CLI, discovery, research,
  scoring model, security, testing, documentation, explicit non-goals)
- Lead scoring model finalized (single authoritative 6-component model, all
  prior informal factors mapped in)
- Data privacy/provenance foundation defined for Phase 1's data model
- Repository & persistence strategy decided (GitHub + Claude Code; Postgres
  via Docker locally in Phase 1, production database configured separately
  in Phase 6)

## In Progress

None. No application code has been written yet.

## Not Started

- Repository creation and initial scaffolding
- Phase 1 implementation (foundation + lead discovery + company research +
  lead scoring + API + CLI)
- Phase 2 — Proposal Engine
- Phase 3 — Outreach Engine
- Phase 4 — WhatsApp AI
- Phase 5 — CRM Dashboard
- Phase 6 — Production Deployment

## Current Task

Awaiting approval to begin Phase 1 implementation.

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
