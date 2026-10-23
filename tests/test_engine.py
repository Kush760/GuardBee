import json
import unittest
from pathlib import Path

from engine import analyze_incident
from retrieval import retrieve_policies

ROOT = Path(__file__).resolve().parents[1]


class TestGuardBeeRulesAndRetrieval(unittest.TestCase):
    def setUp(self):
        self.incidents = json.loads((ROOT / "data" / "incidents.json").read_text(encoding="utf-8"))
        self.policies = json.loads((ROOT / "data" / "policies.json").read_text(encoding="utf-8"))

    def test_high_risk_login_has_explainable_evidence(self):
        result = analyze_incident(self.incidents[0])
        self.assertEqual(result["risk_score"], 95)
        self.assertEqual(result["severity"], "HIGH")
        self.assertIn("EVT-006", result["evidence_ids"])
        self.assertTrue(any(hit["rule_id"] == "GB-RULE-003" for hit in result["rule_hits"]))

    def test_known_ip_case_is_low_risk(self):
        result = analyze_incident(self.incidents[2])
        self.assertEqual(result["risk_score"], 0)
        self.assertEqual(result["severity"], "LOW")
        self.assertEqual(result["evidence_ids"], [])

    def test_unfamiliar_success_is_medium_risk(self):
        result = analyze_incident(self.incidents[1])
        self.assertEqual(result["risk_score"], 40)
        self.assertEqual(result["severity"], "MEDIUM")
        self.assertEqual(result["evidence_ids"], ["EVT-102"])

    def test_three_failures_reach_medium_boundary(self):
        incident = {
            "department": "Support",
            "known_ips": ["203.0.113.5"],
            "events": [
                {"id": "EVT-A", "type": "login_failed", "ip": "203.0.113.5"},
                {"id": "EVT-B", "type": "login_failed", "ip": "203.0.113.5"},
                {"id": "EVT-C", "type": "login_failed", "ip": "203.0.113.5"},
            ],
        }
        result = analyze_incident(incident)
        self.assertEqual(result["risk_score"], 30)
        self.assertEqual(result["severity"], "MEDIUM")

    def test_tfidf_returns_ranked_policy_records(self):
        matches = retrieve_policies("unfamiliar login IP Finance approval", self.policies, top_k=3)
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


if __name__ == "__main__":
    unittest.main()
