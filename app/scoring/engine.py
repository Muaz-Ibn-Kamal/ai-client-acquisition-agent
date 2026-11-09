"""Deterministic lead scoring engine (spec §9).

The engine is authoritative: no LLM or other component sets the final score.
Callers supply *signals* (0.0-1.0 per sub-factor, or ``None`` when unknown)
with optional reasons; the engine turns them into a 100-point score.

Missing-data policy: an unknown sub-factor contributes 0 points (conservative)
and lowers ``confidence``; it is never guessed.
"""

from dataclasses import dataclass, field

# Sub-factors per component, straight from spec §9.
COMPONENT_FACTORS: dict[str, tuple[str, ...]] = {
    "service_fit": ("needs_match", "technology_alignment"),
    "opportunity_strength": (
        "website_quality_problems",
        "ux_problems",
        "design_problems",
        "technical_opportunities",
        "redesign_opportunity",
    ),
    "business_quality": (
        "legitimacy",
        "company_size",
        "business_maturity",
        "stability",
        "market_presence",
    ),
    "need_signal": (
        "hiring_signals",
        "recent_business_changes",
        "product_launches",
        "website_changes",
        "explicit_needs",
        "signal_recency",
    ),
    "project_value_potential": (
        "project_scope",
        "budget_range",
        "business_impact",
        "complexity",
        "recurring_work",
    ),
    "contactability": (
        "public_business_email",
        "public_company_contact",
        "public_professional_contact",
        "response_accessibility",
        "source_reliability",
    ),
}


@dataclass(frozen=True)
class ScoringWeights:
    """Configurable maximum points per component. Must total 100."""

    service_fit: float = 25
    opportunity_strength: float = 25
    business_quality: float = 15
    need_signal: float = 15
    project_value_potential: float = 10
    contactability: float = 10

    def __post_init__(self) -> None:
        if any(w < 0 for w in self.as_dict().values()):
            raise ValueError("weights must be non-negative")
        if abs(sum(self.as_dict().values()) - 100) > 1e-9:
            raise ValueError("scoring weights must sum to 100")

    def as_dict(self) -> dict[str, float]:
        return {name: getattr(self, name) for name in COMPONENT_FACTORS}


@dataclass(frozen=True)
class FactorSignal:
    value: float | None  # 0.0-1.0, or None when unknown
    reason: str = ""

    def __post_init__(self) -> None:
        if self.value is not None and not 0.0 <= self.value <= 1.0:
            raise ValueError(f"signal value must be within 0..1, got {self.value}")


# component -> factor -> signal
ScoringSignals = dict[str, dict[str, FactorSignal]]


@dataclass(frozen=True)
class ComponentResult:
    score: float
    max_score: float
    confidence: float  # share of sub-factors with known values
    reasons: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ScoreResult:
    total_score: float
    components: dict[str, ComponentResult]
    confidence: float
    classification: str

    def component_scores(self) -> dict[str, float]:
        return {name: c.score for name, c in self.components.items()}

    def reasons(self) -> dict[str, list[str]]:
        return {name: c.reasons for name, c in self.components.items()}


def classify(total_score: float) -> str:
    if total_score >= 80:
        return "high_priority"
    if total_score >= 60:
        return "qualified"
    if total_score >= 40:
        return "low_priority"
    return "reject_or_nurture"


def score_lead(signals: ScoringSignals, weights: ScoringWeights | None = None) -> ScoreResult:
    """Compute the 100-point score. Unknown/missing signals count as 0 points."""
    weights = weights or ScoringWeights()
    unknown_components = set(signals) - set(COMPONENT_FACTORS)
    if unknown_components:
        raise ValueError(f"unknown scoring components: {sorted(unknown_components)}")

    components: dict[str, ComponentResult] = {}
    for component, factors in COMPONENT_FACTORS.items():
        provided = signals.get(component, {})
        unknown_factors = set(provided) - set(factors)
        if unknown_factors:
            raise ValueError(f"unknown factors for {component}: {sorted(unknown_factors)}")

        max_score = weights.as_dict()[component]
        known = 0
        points = 0.0
        reasons: list[str] = []
        for factor in factors:
            signal = provided.get(factor)
            if signal is None or signal.value is None:
                reasons.append(f"{factor}: unknown (counted as 0)")
                continue
            known += 1
            points += signal.value
            note = f" - {signal.reason}" if signal.reason else ""
            reasons.append(f"{factor}: {signal.value:.2f}{note}")

        components[component] = ComponentResult(
            score=round(max_score * points / len(factors), 2),
            max_score=max_score,
            confidence=round(known / len(factors), 2),
            reasons=reasons,
        )

    total = round(sum(c.score for c in components.values()), 2)
    # Weight-averaged confidence so low-confidence big components matter more.
    confidence = round(
        sum(c.confidence * c.max_score for c in components.values()) / 100,
        2,
    )
    return ScoreResult(
        total_score=total,
        components=components,
        confidence=confidence,
        classification=classify(total),
    )
