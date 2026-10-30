"""Local TF-IDF retrieval for the sample GuardBee policy library."""

from __future__ import annotations

from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# In the four-passage demo corpus, 0.08 retains tested lexical matches while
# excluding zero/near-zero overlap. Keep it configurable for future corpora.
DEFAULT_MIN_SIMILARITY = 0.08
DEFAULT_TOP_K = 3


def _validate_arguments(
    query: Any, policies: Any, top_k: Any, min_similarity: Any
) -> None:
    if not isinstance(query, str):
        raise TypeError("query must be a string.")
    if isinstance(top_k, bool) or not isinstance(top_k, int):
        raise TypeError("top_k must be an integer.")
    if isinstance(min_similarity, bool) or not isinstance(min_similarity, (int, float)):
        raise TypeError("min_similarity must be a number.")
    if not 0 <= min_similarity <= 1:
        raise ValueError("min_similarity must be between 0 and 1.")
    if not isinstance(policies, list):
        raise TypeError("policies must be a list.")
    for index, policy in enumerate(policies):
        if not isinstance(policy, dict) or not all(
            isinstance(policy.get(field), str) and policy[field].strip()
            for field in ("id", "title", "text")
        ):
            raise ValueError(
                f"policies[{index}] must be an object with non-empty string id, title, and text."
            )


def retrieve_policies(
    query: str,
    policies: list[dict[str, Any]],
    top_k: int = DEFAULT_TOP_K,
    min_similarity: float = DEFAULT_MIN_SIMILARITY,
) -> list[dict[str, Any]]:
    """Return only policy passages that meet the minimum TF-IDF similarity."""
    _validate_arguments(query, policies, top_k, min_similarity)
    if not policies or not query.strip() or top_k <= 0:
        return []
    corpus = [f"{policy['title']} {policy['text']}" for policy in policies]
    try:
        features = TfidfVectorizer(stop_words="english").fit_transform(corpus + [query])
    except ValueError:
        # Only stop words (or no tokens) across corpus and query: nothing can match.
        return []
    scores = cosine_similarity(features[-1], features[:-1]).flatten()
    ranked = sorted(
        (
            index
            for index, score in enumerate(scores)
            if float(score) >= min_similarity
        ),
        key=lambda index: float(scores[index]),
        reverse=True,
    )
    return [
        dict(policies[index], match_score=round(float(scores[index]), 3))
        for index in ranked[:top_k]
    ]
