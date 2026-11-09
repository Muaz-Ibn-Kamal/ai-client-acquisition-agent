import pytest

from app.scoring import COMPONENT_FACTORS, FactorSignal, ScoringWeights, classify, score_lead


def _all(value: float | None) -> dict:
    return {
        component: {f: FactorSignal(value) for f in factors}
        for component, factors in COMPONENT_FACTORS.items()
    }


def test_weights_sum_to_100() -> None:
    assert sum(ScoringWeights().as_dict().values()) == 100


def test_invalid_weights_rejected() -> None:
    with pytest.raises(ValueError):
        ScoringWeights(service_fit=30)  # sums to 105
    with pytest.raises(ValueError):
        ScoringWeights(service_fit=-5, opportunity_strength=55)


def test_perfect_score_is_100() -> None:
    result = score_lead(_all(1.0))
    assert result.total_score == 100
    assert result.confidence == 1
    assert result.classification == "high_priority"
    assert {n: c.score for n, c in result.components.items()} == ScoringWeights().as_dict()


def test_zero_and_all_unknown() -> None:
    assert score_lead(_all(0.0)).total_score == 0
    unknown = score_lead({})
    assert unknown.total_score == 0
    assert unknown.confidence == 0
    assert unknown.classification == "reject_or_nurture"
    assert all("unknown" in r for rs in unknown.reasons().values() for r in rs)


def test_component_math_and_partial_data() -> None:
    signals = {
        "service_fit": {
            "needs_match": FactorSignal(1.0, "asked for a redesign"),
            "technology_alignment": FactorSignal(0.5),
        },
        "contactability": {"public_business_email": FactorSignal(1.0)},  # 4 factors unknown
    }
    result = score_lead(signals)
    assert result.components["service_fit"].score == 18.75  # 25 * 1.5/2
    assert result.components["service_fit"].confidence == 1
    assert result.components["contactability"].score == 2.0  # 10 * 1/5
    assert result.components["contactability"].confidence == 0.2
    assert result.total_score == 20.75
    assert "asked for a redesign" in result.components["service_fit"].reasons[0]
    # weighted confidence: (25*1 + 10*0.2) / 100
    assert result.confidence == 0.27


def test_custom_weights_change_score() -> None:
    weights = ScoringWeights(
        service_fit=50,
        opportunity_strength=10,
        business_quality=10,
        need_signal=10,
        project_value_potential=10,
        contactability=10,
    )
    signals = {
        "service_fit": {"needs_match": FactorSignal(1.0), "technology_alignment": FactorSignal(1.0)}
    }
    assert score_lead(signals, weights).total_score == 50


def test_validation_errors() -> None:
    with pytest.raises(ValueError):
        FactorSignal(1.5)
    with pytest.raises(ValueError):
        score_lead({"bogus": {}})
    with pytest.raises(ValueError):
        score_lead({"service_fit": {"bogus": FactorSignal(1.0)}})


@pytest.mark.parametrize(
    ("score", "label"),
    [
        (100, "high_priority"),
        (80, "high_priority"),
        (79.99, "qualified"),
        (60, "qualified"),
        (59.9, "low_priority"),
        (40, "low_priority"),
        (39.9, "reject_or_nurture"),
        (0, "reject_or_nurture"),
    ],
)
def test_classification_boundaries(score: float, label: str) -> None:
    assert classify(score) == label
