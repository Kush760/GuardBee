"""Policy retrieval stays separate from deterministic risk scoring."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from retrieval import retrieve_policies

ROOT = Path(__file__).resolve().parents[1]


class TestPolicyRetrieval(unittest.TestCase):
    def setUp(self):
        self.policies = json.loads(
            (ROOT / "data" / "policies.json").read_text(encoding="utf-8")
        )

    def test_production_policies_include_optional_enrichment_fields(self):
        for policy in self.policies:
            self.assertIn("description", policy)
            self.assertIn("categories", policy)
            self.assertIn("conditions", policy)
            self.assertIn("investigation_guidance", policy)
            self.assertIsInstance(policy["categories"], list)

    def test_tfidf_returns_ranked_policy_records(self):
        matches = retrieve_policies(
            "unfamiliar login IP Finance approval", self.policies, top_k=3
        )
        self.assertEqual(len(matches), 3)
        self.assertTrue(matches[0]["id"].startswith("POL-"))
        self.assertGreaterEqual(matches[0]["match_score"], matches[-1]["match_score"])

    def test_tfidf_returns_no_match_for_unrelated_or_empty_query(self):
        self.assertEqual(retrieve_policies("quasar nebula", self.policies), [])
        self.assertEqual(retrieve_policies("", self.policies), [])
        self.assertEqual(retrieve_policies("login", []), [])

    def test_tfidf_threshold_can_exclude_weak_matches(self):
        matches = retrieve_policies("unfamiliar login", self.policies, min_similarity=0.99)
        self.assertEqual(matches, [])

    def test_optional_fields_missing_still_retrieve(self):
        minimal = [
            {"id": "POL-X", "title": "Login investigation", "text": "Review unfamiliar IP logins."}
        ]
        matches = retrieve_policies("unfamiliar IP login", minimal, top_k=1)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["id"], "POL-X")

    def test_optional_enrichment_participates_in_search_text(self):
        policies = [
            {
                "id": "POL-A",
                "title": "Generic title",
                "text": "Generic body text.",
                "categories": ["authentication"],
                "conditions": "Only when privilege-escalation-xyz token appears.",
                "investigation_guidance": "Use privilege-escalation-xyz playbook.",
            },
            {
                "id": "POL-B",
                "title": "Other",
                "text": "Unrelated cafeteria menu policy.",
            },
        ]
        matches = retrieve_policies("privilege-escalation-xyz", policies, top_k=1)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["id"], "POL-A")


if __name__ == "__main__":
    unittest.main()
