"""Website analysis: turn public HTML into evidence-backed signals (spec §8).

Everything parsed here is untrusted DATA. Page text is never interpreted as
instructions and never executed. Findings are labeled FACT (directly observed
in the HTML), INFERENCE (heuristic judgement) or UNKNOWN, with a confidence.
"""

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal
from urllib.parse import urlsplit

from bs4 import BeautifulSoup, Tag

Label = Literal["FACT", "INFERENCE", "UNKNOWN"]

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_GENERIC_LOCALPARTS = {
    "info", "contact", "hello", "hi", "office", "sales", "support", "admin",
    "enquiries", "inquiries", "team", "mail", "service", "bookings", "reservations",
}  # fmt: skip
_CTA_WORDS = (
    "contact", "get started", "book", "buy", "shop", "order", "quote", "demo",
    "sign up", "subscribe", "call us", "request", "schedule", "free trial",
)  # fmt: skip
_TECH_MARKERS = {
    "WordPress": ("wp-content", "wp-includes"),
    "Shopify": ("cdn.shopify.com", "shopify.theme"),
    "Wix": ("wixstatic.com", "wix.com"),
    "Squarespace": ("squarespace.com", "static1.squarespace"),
    "Webflow": ("webflow.com", "w-nav"),
    "Next.js": ("/_next/", "__next"),
    "React": ("data-reactroot", "react-dom"),
    "jQuery": ("jquery",),
    "Bootstrap": ("bootstrap",),
}  # fmt: skip


@dataclass(frozen=True)
class Insight:
    claim: str
    evidence: str
    source_url: str
    confidence: float
    label: Label
    code: str = ""
    observed_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be within 0..1")
        if self.label not in ("FACT", "INFERENCE", "UNKNOWN"):
            raise ValueError(f"invalid label {self.label!r}")


@dataclass(frozen=True)
class FoundContact:
    email: str | None
    phone: str | None
    contact_type: Literal["business_inbox", "named_individual"]
    source_url: str


@dataclass
class WebsiteSignals:
    url: str
    title: str | None = None
    meta_description: str | None = None
    headings: list[str] = field(default_factory=list)
    nav_links: list[str] = field(default_factory=list)
    technologies: list[str] = field(default_factory=list)
    has_viewport_meta: bool = False
    uses_https: bool = False
    has_cta: bool = False
    images_total: int = 0
    images_missing_alt: int = 0
    contacts: list[FoundContact] = field(default_factory=list)
    insights: list[Insight] = field(default_factory=list)

    def to_json(self) -> dict[str, object]:
        return {
            "headings": self.headings,
            "nav_links": self.nav_links,
            "technologies": self.technologies,
            "has_viewport_meta": self.has_viewport_meta,
            "uses_https": self.uses_https,
            "has_cta": self.has_cta,
            "images_total": self.images_total,
            "images_missing_alt": self.images_missing_alt,
            "insights": [
                {
                    "claim": i.claim,
                    "evidence": i.evidence,
                    "source_url": i.source_url,
                    "confidence": i.confidence,
                    "label": i.label,
                    "code": i.code,
                    "observed_at": i.observed_at.isoformat(),
                }
                for i in self.insights
            ],
        }


def _clean(text: str | None, limit: int = 300) -> str | None:
    if not text:
        return None
    collapsed = " ".join(text.split())
    return collapsed[:limit] or None


def _site_domain(url: str) -> str:
    host = urlsplit(url).hostname or ""
    return host.removeprefix("www.")


def analyze_html(html: str, url: str) -> WebsiteSignals:
    soup = BeautifulSoup(html, "html.parser")
    lowered = html.lower()
    signals = WebsiteSignals(url=url, uses_https=urlsplit(url).scheme == "https")

    signals.title = _clean(soup.title.string if soup.title else None, 200)
    meta = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
    if isinstance(meta, Tag):
        content = meta.get("content")
        signals.meta_description = _clean(content if isinstance(content, str) else None, 500)

    signals.headings = [
        t for h in soup.find_all(["h1", "h2"])[:15] if (t := _clean(h.get_text(" "), 150))
    ]
    nav = soup.find("nav")
    if isinstance(nav, Tag):
        signals.nav_links = [
            t for a in nav.find_all("a")[:20] if (t := _clean(a.get_text(" "), 60))
        ]

    signals.has_viewport_meta = (
        soup.find("meta", attrs={"name": re.compile("viewport", re.I)}) is not None
    )
    signals.technologies = sorted(
        tech for tech, markers in _TECH_MARKERS.items() if any(m in lowered for m in markers)
    )

    cta_elements = soup.find_all(["a", "button"])
    signals.has_cta = any(
        any(w in (el.get_text(" ") or "").lower() for w in _CTA_WORDS) for el in cta_elements
    )

    images = soup.find_all("img")
    signals.images_total = len(images)
    signals.images_missing_alt = sum(1 for i in images if not str(i.get("alt") or "").strip())

    signals.contacts = _extract_contacts(soup, url)
    signals.insights = _build_insights(signals, url)
    return signals


def _extract_contacts(soup: BeautifulSoup, url: str) -> list[FoundContact]:
    """Public business contact details displayed on the page (mailto:/tel: and visible text)."""
    emails: dict[str, None] = {}
    phones: dict[str, None] = {}
    for a in soup.find_all("a", href=True):
        href = str(a["href"])
        if href.lower().startswith("mailto:"):
            emails[href[7:].split("?")[0].strip().lower()] = None
        elif href.lower().startswith("tel:"):
            phones[href[4:].strip()] = None
    for match in _EMAIL_RE.findall(soup.get_text(" ")):
        emails[match.lower()] = None

    contacts = []
    for email in emails:
        if not email:
            continue
        local = email.split("@")[0]
        ctype: Literal["business_inbox", "named_individual"] = (
            "business_inbox" if local in _GENERIC_LOCALPARTS else "named_individual"
        )
        contacts.append(FoundContact(email=email, phone=None, contact_type=ctype, source_url=url))
    for phone in phones:
        contacts.append(
            FoundContact(email=None, phone=phone, contact_type="business_inbox", source_url=url)
        )
    return contacts


def _build_insights(s: WebsiteSignals, url: str) -> list[Insight]:
    out: list[Insight] = []

    def add(code: str, claim: str, evidence: str, confidence: float, label: Label) -> None:
        out.append(Insight(claim, evidence, url, confidence, label, code))

    if not s.uses_https:
        add(
            "no_https",
            "Site is not served over HTTPS.",
            f"Final URL scheme is {urlsplit(url).scheme}.",
            0.95,
            "FACT",
        )
    if not s.has_viewport_meta:
        add(
            "no_viewport",
            "Site may not be mobile-responsive.",
            "No <meta name='viewport'> tag found on the homepage.",
            0.7,
            "INFERENCE",
        )
    if not s.title:
        add("no_title", "Homepage has no title tag.", "<title> missing or empty.", 0.95, "FACT")
    if not s.meta_description:
        add(
            "no_meta_description",
            "Homepage has no meta description (SEO basics).",
            "No meta description tag.",
            0.9,
            "FACT",
        )
    if not s.has_cta:
        add(
            "no_cta",
            "Homepage may lack a clear conversion CTA.",
            "No link/button text matching common CTA wording was found.",
            0.6,
            "INFERENCE",
        )
    if s.images_total and s.images_missing_alt / s.images_total >= 0.5:
        add(
            "images_missing_alt",
            "Many images lack alt text (accessibility/SEO).",
            f"{s.images_missing_alt} of {s.images_total} images have no alt text.",
            0.9,
            "FACT",
        )
    if s.technologies:
        add(
            "technologies",
            "Technology indicators detected.",
            ", ".join(s.technologies) + " markers present in page source.",
            0.7,
            "INFERENCE",
        )
    if not s.contacts:
        add(
            "no_contacts",
            "No public contact details found on the homepage.",
            "No mailto:/tel: links or visible email addresses on this page.",
            0.6,
            "INFERENCE",
        )
    return out
