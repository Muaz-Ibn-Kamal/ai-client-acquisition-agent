"""Command-line interface. Thin wrapper over the same services the API uses.

uv run python -m app.cli discover --provider csv --csv-file leads.csv
uv run python -m app.cli discover --provider google_places --query "dental clinics Toronto"
uv run python -m app.cli research --company-id <UUID>
uv run python -m app.cli score --lead-id <UUID>
uv run python -m app.cli top-leads --min-score 60
"""

import argparse
import asyncio
import sys
import uuid
from pathlib import Path

from app.db.session import get_sessionmaker
from app.repositories import company as company_repo
from app.repositories import lead as lead_repo
from app.services.discovery.base import LeadSourceProvider, ProviderUnavailableError
from app.services.discovery.providers import CsvProvider, GooglePlacesProvider
from app.services.discovery.service import run_discovery
from app.services.research import ResearchError, research_company
from app.services.scoring import score_lead_record


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="app.cli", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    d = sub.add_parser("discover", help="discover companies and create leads")
    d.add_argument("--provider", choices=["csv", "google_places"], required=True)
    d.add_argument("--query", help="search query (google_places)")
    d.add_argument(
        "--csv-file", type=Path, help="CSV with name,website[,industry,country,location]"
    )
    d.add_argument("--limit", type=int, default=20)

    r = sub.add_parser("research", help="research a company's public website")
    r.add_argument("--company-id", type=uuid.UUID, required=True)

    s = sub.add_parser("score", help="score a lead from research data")
    s.add_argument("--lead-id", type=uuid.UUID, required=True)

    t = sub.add_parser("top-leads", help="list leads ranked by latest score")
    t.add_argument("--min-score", type=float, default=0)
    t.add_argument("--limit", type=int, default=20)
    return parser


async def _run(args: argparse.Namespace) -> int:
    async with get_sessionmaker()() as session:
        if args.command == "discover":
            provider: LeadSourceProvider
            if args.provider == "csv":
                if not args.csv_file:
                    print("--csv-file is required for provider csv", file=sys.stderr)
                    return 2
                provider = CsvProvider(args.csv_file.read_text(encoding="utf-8"))
            else:
                provider = GooglePlacesProvider()
            try:
                res = await run_discovery(session, provider, args.query, args.limit)
            except ProviderUnavailableError as exc:
                print(f"provider unavailable: {exc}", file=sys.stderr)
                return 1
            await session.commit()
            print(
                f"{res.provider}: found={res.found} new={res.new_companies} "
                f"duplicates={res.duplicates} invalid={res.invalid}"
            )
            for lead_id in res.lead_ids:
                print(f"  lead {lead_id}")
        elif args.command == "research":
            company = await company_repo.get(session, args.company_id)
            if company is None:
                print("company not found", file=sys.stderr)
                return 1
            try:
                out = await research_company(session, company)
            except ResearchError as exc:
                print(f"research failed: {exc}", file=sys.stderr)
                return 1
            await session.commit()
            print(
                f"{company.domain}: contacts_added={out.contacts_added} "
                f"opportunities_added={out.opportunities_added}"
            )
            for i in out.signals.insights:
                print(f"  [{i.label} {i.confidence:.2f}] {i.claim} -- {i.evidence}")
        elif args.command == "score":
            lead = await lead_repo.get_lead(session, args.lead_id)
            if lead is None:
                print("lead not found", file=sys.stderr)
                return 1
            saved = await score_lead_record(session, lead)
            await session.commit()
            print(f"total={saved.total_score} confidence={saved.confidence}")
        elif args.command == "top-leads":
            leads, total = await lead_repo.list_leads(
                session, min_score=args.min_score if args.min_score > 0 else None,
                country=None, service=None, status=None, sort="score", limit=args.limit, offset=0,
            )  # fmt: skip
            print(f"{total} lead(s)")
            for lead in leads:
                score = lead_repo.latest_score(lead)
                shown = f"{score.total_score:5.1f}" if score else "  n/a"
                print(f"{shown}  {lead.company.domain}  {lead.id}")
    return 0


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(_run(_parser().parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main())
