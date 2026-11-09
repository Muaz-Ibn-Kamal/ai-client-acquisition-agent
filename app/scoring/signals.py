"""Derive scoring signals from observed research data.

Only factors that can be justified from public, observed data are filled in.
Everything else stays unknown (None) until an analyst supplies it via
overrides. This keeps the score honest: unknown never becomes a guess.
"""

from typing import Any

from app.models import Contact, WebsiteAnalysis
from app.scoring.engine import FactorSignal, ScoringSignals

_OUR_STACKS = {"WordPress", "Shopify", "React", "Next.js"}
_PROBLEM_CODES = {"no_https", "no_title", "no_meta_description", "images_missing_alt"}


def derive_signals(
    analysis: WebsiteAnalysis | None,
    contacts: list[Contact],
) -> ScoringSignals:
    signals: ScoringSignals = {}
    if analysis is None:
        return signals

    data: dict[str, Any] = analysis.signals or {}
    insights = data.get("insights", [])
    codes = {i.get("code") for i in insights}
    techs = set(data.get("technologies", []))

    problems = len(_PROBLEM_CODES & codes)
    signals["opportunity_strength"] = {
        "website_quality_problems": FactorSignal(
            min(1.0, problems / 3), f"{problems} basic quality issues observed"
        ),
        "ux_problems": FactorSignal(
            1.0 if "no_viewport" in codes else 0.0,
            "no viewport meta tag" if "no_viewport" in codes else "viewport meta present",
        ),
        "technical_opportunities": FactorSignal(
            1.0 if "no_https" in codes else 0.0,
            "not served over HTTPS" if "no_https" in codes else "HTTPS in use",
        ),
    }

    signals["service_fit"] = {}
    if techs & _OUR_STACKS:
        signals["service_fit"]["technology_alignment"] = FactorSignal(
            1.0, f"detected {', '.join(sorted(techs & _OUR_STACKS))}"
        )

    signals["business_quality"] = {
        "legitimacy": FactorSignal(
            1.0 if data.get("uses_https") else 0.5,
            "site reachable; HTTPS" if data.get("uses_https") else "site reachable over HTTP only",
        )
    }

    usable = [c for c in contacts if c.is_public_business_contact and not c.is_suppressed]
    has_business_email = any(c.email and c.contact_type == "business_inbox" for c in usable)
    has_named_email = any(c.email and c.contact_type == "named_individual" for c in usable)
    has_any = bool(usable)
    signals["contactability"] = {
        "public_business_email": FactorSignal(
            1.0 if has_business_email else 0.6 if has_named_email else 0.0,
            "business inbox published" if has_business_email else "no business inbox found",
        ),
        "public_company_contact": FactorSignal(1.0 if has_any else 0.0),
    }
    if has_any:
        signals["contactability"]["source_reliability"] = FactorSignal(
            0.8, "published on the company's own website"
        )
    return signals


def merge_overrides(base: ScoringSignals, overrides: ScoringSignals) -> ScoringSignals:
    """Analyst-supplied signals take precedence over derived ones."""
    merged: ScoringSignals = {c: dict(f) for c, f in base.items()}
    for component, factors in overrides.items():
        merged.setdefault(component, {}).update(factors)
    return merged
