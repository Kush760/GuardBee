"""Local TF-IDF retrieval for the sample GuardBee policy library."""

from __future__ import annotations

from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# In the four-passage demo corpus, 0.08 retains tested lexical matches while
# excluding zero/near-zero overlap. Keep it configurable for future corpora.
DEFAULT_MIN_SIMILARITY = 0.08


def _policy_search_text(policy: dict[str, Any]) -> str:
    """Build TF-IDF text from required fields plus optional enrichment."""
    categories = policy.get("categories") or []
    category_text = " ".join(
        item for item in categories if isinstance(item, str) and item.strip()
    )
    parts = [
        str(policy.get("title") or ""),
        str(policy.get("description") or ""),
        str(policy.get("text") or ""),
        category_text,
        str(policy.get("conditions") or ""),
        str(policy.get("investigation_guidance") or ""),
    ]
    return " ".join(part for part in parts if part.strip())


def retrieve_policies(
    query: str,
    policies: list[dict[str, Any]],
    top_k: int = 3,
    min_similarity: float = DEFAULT_MIN_SIMILARITY,
) -> list[dict[str, Any]]:
    """Return only policy passages that meet the minimum TF-IDF similarity.

    Retrieval stays separate from deterministic risk scoring in ``engine.py``.
    """
    if not policies or not query.strip() or top_k <= 0:
        return []
    if not 0 <= min_similarity <= 1:
        raise ValueError("min_similarity must be between 0 and 1.")
    corpus = [_policy_search_text(policy) for policy in policies]
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
