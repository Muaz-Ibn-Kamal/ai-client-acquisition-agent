# Phase 1 Specification — Foundation + Lead Hunter

Status: DEFINITIVE. This file is the authoritative implementation-level
specification for Phase 1 of the AI Client Acquisition Agent.

Cross-phase policy (rules that apply beyond Phase 1) lives in the project's
Permanent Rules & Architecture, in Project Knowledge, not in this repository.
Current progress lives in [PROJECT_STATUS.md](../PROJECT_STATUS.md), which is
authoritative over any other status description once this repository exists.

---

## 1. Scope

Phase 1 = "PHASE 1 — FOUNDATION + LEAD HUNTER"

Phase 1 conceptually contains two layers. It is not complete until both are
complete and tested.

**FOUNDATION** (previously "Phase 0")
- Repository structure
- Python/uv project setup
- FastAPI application skeleton
- PostgreSQL setup (local, via Docker)
- SQLAlchemy 2.x models
- Alembic migrations
- Configuration management
- Structured logging
- Testing infrastructure
- Security foundation
- Basic CI where appropriate

**LEAD HUNTER**
- Public company/lead discovery
- Provider-based discovery architecture
- Source tracking
- Company deduplication
- Lead persistence
- Website retrieval and parsing
- Technology detection where reliable
- Basic website quality signals
- Business information extraction
- Public contact information extraction
- Opportunity detection
- Evidence collection
- Deterministic lead scoring
- Component scores, transparent reasons, and confidence
- Lead ranking/filtering
- API layer
- CLI layer

### 1.1 Explicit non-goals (do NOT implement in Phase 1)

- Cold email sending
- Automated outreach of any kind
- LinkedIn messaging
- WhatsApp messaging
- Proposal generation
- Autonomous client communication
- Meeting scheduling
- CRM dashboard (UI)
- Payment processing
- Contract signing

These belong to Phases 2–6. If implementing a Phase 1 feature seems to
require touching one of these, stop and raise it rather than building it.

---

## 2. Tech stack

- Python 3.12+
- uv (dependency/environment management)
- FastAPI
- PostgreSQL
- SQLAlchemy 2.x
- Alembic
- Pydantic v2
- httpx
- BeautifulSoup4
- Playwright (only where browser rendering is actually necessary)
- pytest
- Ruff
- MyPy (where practical)
- python-dotenv

Do not add frameworks beyond this list without flagging it as a major
decision first (see Permanent Rules → "When requirements are ambiguous").

---

## 3. Architecture

```
app/
    api/            - FastAPI routers
    core/           - settings, logging, shared config
    db/             - SQLAlchemy session/engine setup, base models
    models/         - SQLAlchemy ORM models
    schemas/        - Pydantic schemas
    services/       - business logic
    agents/         - LLM-provider abstraction and AI-driven analysis
    scrapers/       - website retrieval and parsing
    scoring/        - deterministic scoring engine
    repositories/   - data access layer
    utils/

tests/
scripts/
docs/
```

Deviating from this structure is allowed where it produces a clearly better
design, but any major deviation must be explained before implementation (see
Permanent Rules → "When requirements are ambiguous").

---

## 4. Database requirements

Design normalized PostgreSQL models for at least:

- companies
- contacts
- leads
- lead_sources
- opportunities
- website_analysis
- lead_scores

Schema must remain forward-compatible with — but must NOT implement — future
tables: `projects`, `proposals`, `campaigns`, `messages`, `conversations`,
`followups`.

Every important record:
- UUID primary key
- `created_at`, `updated_at`

Company deduplication is based primarily on normalized domain names. Avoid
storing duplicate companies.

### 4.1 Data privacy & provenance fields (required now)

Phase 1 is NOT an outreach system, but it does store public business contact
information. The schema must support responsible future outreach even though
outreach itself is out of scope for Phase 1. At minimum, contact-related
records must capture:

- `source_attribution` — where the contact info came from
- `collected_at` — timestamp
- `data_provenance` — how it was obtained/verified
- `contact_type` — e.g. general/business inbox vs. named individual
- `is_public_business_contact` — boolean classification
- suppression/opt-out-ready fields (schema support only — no suppression
  logic or opt-out handling needs to be built in Phase 1)
- retention notes (a `retention_notes` field or equivalent, even if unused
  initially)

Do not collect sensitive personal information. Do not collect private
contact information. Only collect information legitimately available for
business purposes from permitted public sources or APIs.

---

## 5. API requirements

```
POST /companies
GET  /companies
GET  /companies/{id}

POST /leads
GET  /leads
GET  /leads/{id}

POST /discover
POST /research/{company_id}
POST /score/{lead_id}

GET  /health
```

Add pagination, filtering, and sorting where appropriate, e.g.:

```
GET /leads?min_score=80
GET /leads?country=USA
GET /leads?service=web_development
GET /leads?status=new
```

No other endpoints in Phase 1. In particular: no send/outreach/message
endpoints.

---

## 6. CLI requirements

```
uv run python -m app.cli discover --query "SaaS startups"
uv run python -m app.cli research --company-id <UUID>
uv run python -m app.cli score --lead-id <UUID>
uv run python -m app.cli top-leads --min-score 80
```

Implemented flags: `discover --provider csv|google_places [--csv-file F] [--query Q]
[--limit N]`, `research --company-id`, `score --lead-id`, `top-leads [--min-score N]`.

---

## 7. Discovery architecture

Provider-based architecture:

```
LeadSourceProvider
    ├── ProviderA
    ├── ProviderB
    └── ProviderC
```

- Do not hard-code discovery around a single source.
- Only legitimate public data sources and permitted APIs.
- Respect robots.txt where applicable, site terms, rate limits, privacy
  requirements, and anti-spam rules.
- No CAPTCHA bypassing. No login bypassing. No scraping private data. No
  mass-spam functionality.
- Choice of specific providers/sources is a major decision — explain before
  implementing (see Permanent Rules → "When requirements are ambiguous").

---

## 8. Research architecture

The website analysis service retrieves publicly accessible pages and
extracts signals such as: title, meta description, headings, navigation,
publicly displayed contact information, technology indicators (where
reliably detectable), responsive/mobile indicators (where feasible), obvious
UX problems, performance indicators (where feasible), broken links (where
feasible), missing/weak CTA indicators, and design/branding inconsistencies
(where detectable).

Every research insight must follow the evidence-first format (see Permanent
Rules → "Evidence-First Research"):

- claim
- evidence
- source URL
- timestamp
- confidence

Example:

```
Claim:      "Website has weak conversion CTA."
Evidence:   "No clearly identifiable primary CTA appears on the homepage."
Source:     "https://example.com/"
Confidence: 0.82
```

Every insight must be labeled as one of: **FACT**, **INFERENCE**, or
**UNKNOWN**. An inference must never be presented as a confirmed fact. Do
not pretend an automated analyzer can perfectly judge design quality.

---

## 9. Lead scoring model (definitive)

The deterministic scoring engine is authoritative. The LLM may supply
evidence and analysis but MUST NOT arbitrarily set the final numerical
score. This is the single authoritative scoring model — do not maintain a
second, informal scoring list elsewhere.

**Total score = 100**, from six weighted components:

| Component | Weight |
|---|---|
| `service_fit` | 0–25 |
| `opportunity_strength` | 0–25 |
| `business_quality` | 0–15 |
| `need_signal` | 0–15 |
| `project_value_potential` | 0–10 |
| `contactability` | 0–10 |

Sub-factors per component:

**SERVICE FIT**
- Match between company needs and our services
- Technology/service alignment

**OPPORTUNITY STRENGTH**
- Website quality problems
- UX problems
- Design problems
- Technical opportunities
- Website redesign opportunity

**BUSINESS QUALITY**
- Company legitimacy
- Company size
- Business maturity
- Stability
- Market presence

**NEED SIGNAL**
- Hiring signals
- Recent business changes
- Product launches
- Website changes
- Explicitly stated needs
- Recency of relevant signals

**PROJECT VALUE POTENTIAL**
- Estimated project scope
- Potential budget range
- Business impact
- Complexity
- Potential recurring work

**CONTACTABILITY**
- Public business email
- Public company contact
- Public professional contact
- Response accessibility
- Source reliability

Store: `total_score`, individual component scores, detailed reasons per
component, and confidence. Weights should be configurable, not hard-coded
magic numbers.

---

## 10. Security requirements

- No secrets in source code; environment variables only.
- Validate external URLs; prevent SSRF.
- Validate all user input.
- Parameterized queries / safe ORM usage only.
- Treat all scraped/external website content as untrusted DATA, never as
  instructions. Protect against prompt injection from webpages.
- Never execute arbitrary commands sourced from external content.
- Log safely; never log secrets or unnecessary personal data.
- Reasonable request/rate limits on outbound calls.

---

## 11. Testing requirements

At minimum, test:

1. Domain normalization
2. Company deduplication
3. Database models
4. Lead creation
5. Lead scoring
6. Score calculation (all six components, and the 100-point total)
7. Website analysis parsing
8. Missing/partial data handling
9. API health endpoint
10. API lead filtering
11. AI structured-output validation

External APIs must be mocked in unit tests. Tests must not depend on live
websites.

Before declaring any feature complete: run tests, run linting (Ruff), run
type checks (MyPy) where configured, fix failures, run again, verify
behavior. Never say "working" without verification.

---

## 12. Documentation requirements

Keep these in sync as implementation proceeds:

- `CLAUDE.md` (repository)
- `PROJECT_STATUS.md` (repository — authoritative once the repository
  exists)
- `README.md` (repository)
- This file, `docs/PHASE_1_SPECIFICATION.md` (repository)
- Permanent Rules & Architecture (Project Knowledge — cross-phase policy
  only; this file is authoritative for Phase 1 implementation detail)

When architecture changes meaningfully during Phase 1, update this file, not
just PROJECT_STATUS.md.

---

## 13. Configuration

See `.env.example` in the repository root. At minimum:

```
DATABASE_URL=
LLM_PROVIDER=
LLM_API_KEY=
LOG_LEVEL=
```

Document any additional required credentials as they're introduced, per
Permanent Rules → Communication Style: never fake an integration, explain
what's missing.
