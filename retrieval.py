"""Local TF-IDF retrieval for the sample GuardBee policy library."""

from __future__ import annotations

from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# In the four-passage demo corpus, 0.08 retains tested lexical matches while
# excluding zero/near-zero overlap. Keep it configurable for future corpora.
DEFAULT_MIN_SIMILARITY = 0.08


def retrieve_policies(
    query: str,
    policies: list[dict[str, Any]],
    top_k: int = 3,
    min_similarity: float = DEFAULT_MIN_SIMILARITY,
) -> list[dict[str, Any]]:
    """Return only policy passages that meet the minimum TF-IDF similarity."""
    if not policies or not query.strip() or top_k <= 0:
        return []
    if not 0 <= min_similarity <= 1:
        raise ValueError("min_similarity must be between 0 and 1.")
    corpus = [f"{policy['title']} {policy['text']}" for policy in policies]
    features = TfidfVectorizer(stop_words="english").fit_transform(corpus + [query])
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
