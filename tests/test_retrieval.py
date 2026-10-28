import copy
import json
import unittest
from pathlib import Path

from engine import analyze_incident
from retrieval import DEFAULT_MIN_SIMILARITY, DEFAULT_TOP_K, retrieve_policies

ROOT = Path(__file__).resolve().parents[1]


def incident_query(incident):
    """Mirror the query app.py builds for each incident."""
    analysis = analyze_incident(incident)
    return " ".join(
        [incident["title"], incident["department"], *analysis["flags"], analysis["suggested_action"]]
    )


class TestPolicyRetrieval(unittest.TestCase):
    def setUp(self):
        self.incidents = json.loads((ROOT / "data" / "incidents.json").read_text(encoding="utf-8"))
        self.policies = json.loads((ROOT / "data" / "policies.json").read_text(encoding="utf-8"))

    def test_documented_defaults(self):
        self.assertEqual(DEFAULT_TOP_K, 3)
        self.assertEqual(DEFAULT_MIN_SIMILARITY, 0.08)

    def test_bundled_incidents_retrieve_expected_policy_ids(self):
        expected = {
            "INC-1001": ["POL-001", "POL-002"],
            "INC-1002": ["POL-001", "POL-004"],
            "INC-1003": ["POL-001"],
            "INC-1004": ["POL-001"],
            "INC-1005": ["POL-001"],
            "INC-1006": ["POL-001"],
            "INC-1007": ["POL-001", "POL-004"],
            "INC-1008": ["POL-001"],
            "INC-1009": ["POL-005"],
            "INC-1010": ["POL-001", "POL-004"],
            "INC-1012": ["POL-001"],
            "INC-1013": ["POL-001", "POL-002"],
            "INC-1014": ["POL-001", "POL-004"],
        }
        for incident in self.incidents:
            with self.subTest(incident=incident["id"]):
                matches = retrieve_policies(incident_query(incident), self.policies)
                self.assertEqual([match["id"] for match in matches], expected[incident["id"]])
                scores = [match["match_score"] for match in matches]
                self.assertEqual(scores, sorted(scores, reverse=True))
                self.assertTrue(all(score >= DEFAULT_MIN_SIMILARITY for score in scores))

    def test_finance_policy_only_reaches_finance_incidents(self):
        for incident in self.incidents:
            with self.subTest(incident=incident["id"]):
                ids = [match["id"] for match in retrieve_policies(incident_query(incident), self.policies)]
                self.assertEqual("POL-002" in ids, incident["department"] == "Finance")

    def test_every_bundled_incident_has_policy_context(self):
        # Without a policy match the AI report is blocked, so every incident needs at least one.
        for incident in self.incidents:
            with self.subTest(incident=incident["id"]):
                self.assertTrue(retrieve_policies(incident_query(incident), self.policies))

    def test_does_not_pad_results_with_below_threshold_policies(self):
        matches = retrieve_policies(incident_query(self.incidents[2]), self.policies)
        self.assertEqual(len(matches), 1)

    def test_top_k_truncates_ranked_results(self):
        query = "unfamiliar login IP Finance approval"
        full = retrieve_policies(query, self.policies, top_k=len(self.policies), min_similarity=0)
        self.assertEqual(retrieve_policies(query, self.policies, top_k=1), full[:1])
        self.assertLessEqual(len(retrieve_policies(query, self.policies)), DEFAULT_TOP_K)

    def test_non_positive_top_k_returns_nothing(self):
        self.assertEqual(retrieve_policies("login", self.policies, top_k=0), [])
        self.assertEqual(retrieve_policies("login", self.policies, top_k=-1), [])

    def test_threshold_is_inclusive(self):
        matches = retrieve_policies(
            "unfamiliar login IP", self.policies, top_k=len(self.policies), min_similarity=0
        )
        self.assertEqual(len(matches), len(self.policies))
        self.assertEqual(matches[-1]["match_score"], 0.0)

    def test_whitespace_query_returns_nothing(self):
        self.assertEqual(retrieve_policies("   \n", self.policies), [])

    def test_stop_word_only_corpus_and_query_return_nothing(self):
        policies = [{"id": "POL-X", "title": "the", "text": "and of"}]
        self.assertEqual(retrieve_policies("the and", policies), [])

    def test_equal_scores_keep_corpus_order(self):
        policies = [
            {"id": "POL-B", "title": "Login review", "text": "Review unfamiliar login."},
            {"id": "POL-A", "title": "Login review", "text": "Review unfamiliar login."},
        ]
        matches = retrieve_policies("unfamiliar login", policies)
        self.assertEqual([match["id"] for match in matches], ["POL-B", "POL-A"])

    def test_results_are_deterministic_and_inputs_unchanged(self):
        original = copy.deepcopy(self.policies)
        first = retrieve_policies("unfamiliar login IP Finance", self.policies)
        second = retrieve_policies("unfamiliar login IP Finance", self.policies)
        self.assertEqual(first, second)
        self.assertEqual(self.policies, original)
        self.assertEqual(set(first[0]), set(self.policies[0]) | {"match_score"})  # policy fields pass through

    def test_invalid_arguments_are_rejected(self):
        cases = [
            (TypeError, (None, self.policies), {}),
            (TypeError, ("login", self.policies), {"top_k": "3"}),
            (TypeError, ("login", self.policies), {"top_k": True}),
            (TypeError, ("login", self.policies), {"min_similarity": "0.1"}),
            (ValueError, ("login", self.policies), {"min_similarity": 1.5}),
            (ValueError, ("login", self.policies), {"min_similarity": float("nan")}),
            (TypeError, ("login", None), {}),
        ]
        for error, args, kwargs in cases:
            with self.subTest(args=args[0], kwargs=kwargs):
                with self.assertRaises(error):
                    retrieve_policies(*args, **kwargs)

    def test_malformed_policy_entries_are_rejected(self):
        for policy in (
            {"id": "POL-X", "title": "Login"},
            {"id": "POL-X", "title": "Login", "text": "   "},
            {"id": 7, "title": "Login", "text": "Review login."},
            "POL-X Login",
        ):
            with self.subTest(policy=policy):
                with self.assertRaisesRegex(ValueError, r"policies\[0\]"):
                    retrieve_policies("login", [policy])


if __name__ == "__main__":
    unittest.main()
