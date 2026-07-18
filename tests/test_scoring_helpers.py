from src.domain.models import ScoreBreakdown
from src.ranking.scorer import WEIGHTS, ResumeRanker


def test_experience_score_caps_at_one():
    assert ResumeRanker._experience_score(5, 3) == 1.0
    assert ResumeRanker._experience_score(1.5, 3) == 0.5


def test_calibrated_cosine():
    assert ResumeRanker._calibrate_cosine(0.2) == 0
    assert ResumeRanker._calibrate_cosine(0.8) == 1


def test_conceptual_match_score_name_and_weight():
    assert "conceptual_match_score" in ScoreBreakdown.model_fields
    assert WEIGHTS["conceptual_match_score"] == 0.30
    assert sum(WEIGHTS.values()) == 1.0
