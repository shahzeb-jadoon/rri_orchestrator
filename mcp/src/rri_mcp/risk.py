"""Self-consistency risk scoring.

This is the *honest* version of the "quantitative risk" idea: instead of trusting
one LLM draft, we sample several and measure how much they disagree. High
disagreement => high uncertainty => route to a human (HITL).

This is a real, citable technique (self-consistency / sample-variance as an
uncertainty proxy). It is NOT "actuarial survival modelling" - don't call it that.
What it genuinely shares with a quant/actuarial mindset is treating a model output
as a distribution with a variance you must measure and bound before acting on it.
"""

from __future__ import annotations

import re
from itertools import combinations
from typing import Callable

LLMFn = Callable[[list[dict], str], str]


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _jaccard(a: str, b: str) -> float:
    """Token-level Jaccard similarity in [0, 1] (1.0 == identical token sets)."""
    ta, tb = _tokens(a), _tokens(b)
    if not ta and not tb:
        return 1.0
    inter = len(ta & tb)
    union = len(ta | tb)
    return inter / union if union else 1.0


def disagreement_score(samples: list[str]) -> float:
    """Mean pairwise dissimilarity across samples -> risk in [0, 1].

    0.0 = all samples agree (low risk); 1.0 = total disagreement (high risk).
    A single sample has no measurable variance, so we return 0.0.
    """
    if len(samples) < 2:
        return 0.0
    sims = [_jaccard(a, b) for a, b in combinations(samples, 2)]
    mean_similarity = sum(sims) / len(sims)
    return round(1.0 - mean_similarity, 4)


def sample_and_score(
    messages: list[dict],
    llm: LLMFn,
    n: int = 5,
    model: str = "gpt-4o-mini",
) -> tuple[str, float]:
    """Draw `n` completions, score their disagreement, return (best_draft, risk).

    `best_draft` is just the first sample here; a fuller implementation could pick
    the medoid (sample most similar to the others).
    """
    samples = [llm(messages, model) for _ in range(max(1, n))]
    return samples[0], disagreement_score(samples)
