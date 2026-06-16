"""Unit tests for the self-consistency risk scorer (pure, offline)."""

from rri_mcp.risk import disagreement_score, sample_and_score


def test_identical_samples_are_zero_risk():
    assert disagreement_score(["go left now", "go left now", "go left now"]) == 0.0


def test_single_sample_has_no_measurable_variance():
    assert disagreement_score(["only one"]) == 0.0


def test_disjoint_samples_are_max_risk():
    assert disagreement_score(["alpha beta", "gamma delta"]) == 1.0


def test_partial_overlap_is_between():
    score = disagreement_score(["turn left at the light", "turn right at the light"])
    assert 0.0 < score < 1.0


def test_sample_and_score_uses_injected_llm():
    fake = lambda messages, model: "deterministic answer"
    draft, risk = sample_and_score([{"role": "user", "content": "hi"}], fake, n=4)
    assert draft == "deterministic answer"
    assert risk == 0.0
