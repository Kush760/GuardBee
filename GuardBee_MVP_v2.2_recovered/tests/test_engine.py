import importlib.util
import json
import unittest
from pathlib import Path

from engine import (
    DEFAULT_FAILURE_BURST_WINDOW_MINUTES,
    analyze_incident,
)

_HAS_SKLEARN = importlib.util.find_spec("sklearn") is not None

ROOT = Path(__file__).resolve().parents[1]


def _event(event_id: str, time_utc: str, event_type: str, ip: str, country: str = "Unknown"):
    return {
        "id": event_id,
        "time_utc": time_utc,
        "type": event_type,
        "ip": ip,
        "country": country,
    }


class TestGuardBeeDetectionEngine(unittest.TestCase):
    def setUp(self):
        self.incidents = json.loads((ROOT / "data" / "incidents.json").read_text(encoding="utf-8"))

    def test_production_suspicious_incident_has_explainable_evidence(self):
        result = analyze_incident(self.incidents[0])
        self.assertEqual(result["classification"], "SUSPICIOUS")
        self.assertEqual(result["risk_score"], 70)
        self.assertEqual(result["severity"], "HIGH")
        self.assertEqual(result["investigation_priority"], "HIGH")
        self.assertIn("EVT-006", result["evidence_ids"])
        rule_ids = [hit["rule_id"] for hit in result["rule_hits"]]
        self.assertIn("GB-RULE-001", rule_ids)
        self.assertIn("GB-RULE-003", rule_ids)
        self.assertNotIn("GB-RULE-004", rule_ids)
        # Unfamiliar success is covered by fail-then-success; do not stack RULE-002 points.
        self.assertFalse(
            any(hit["rule_id"] == "GB-RULE-002" and hit["points"] > 0 for hit in result["rule_hits"])
        )

    def test_normal_known_ip_login_has_no_low_severity(self):
        result = analyze_incident(self.incidents[2])
        self.assertEqual(result["classification"], "NORMAL")
        self.assertEqual(result["risk_score"], 0)
        self.assertIsNone(result["severity"])
        self.assertEqual(result["investigation_priority"], "NONE")
        self.assertEqual(result["evidence_ids"], [])

    def test_unfamiliar_ip_alone_is_insufficient_evidence(self):
        result = analyze_incident(self.incidents[1])
        self.assertEqual(result["classification"], "INSUFFICIENT_EVIDENCE")
        self.assertEqual(result["risk_score"], 0)
        self.assertIsNone(result["severity"])
        self.assertEqual(result["investigation_priority"], "LOW")
        self.assertEqual(result["evidence_ids"], ["EVT-102"])
        self.assertTrue(any(hit["rule_id"] == "GB-RULE-002" for hit in result["rule_hits"]))

    def test_normal_repeated_known_successes(self):
        incident = {
            "department": "Analytics",
            "known_ips": ["203.0.113.120"],
            "events": [
                _event("EVT-A", "2026-10-20T09:00:00Z", "login_success", "203.0.113.120"),
                _event("EVT-B", "2026-10-20T09:02:00Z", "login_success", "203.0.113.120"),
                _event("EVT-C", "2026-10-20T09:04:00Z", "login_success", "203.0.113.120"),
            ],
        }
        result = analyze_incident(incident)
        self.assertEqual(result["classification"], "NORMAL")
        self.assertEqual(result["risk_score"], 0)
        self.assertIsNone(result["severity"])

    def test_known_ip_failure_then_success_is_suspicious(self):
        incident = {
            "department": "Support",
            "known_ips": ["203.0.113.122"],
            "events": [
                _event("EVT-1", "2026-10-20T11:00:00Z", "login_failed", "203.0.113.122"),
                _event("EVT-2", "2026-10-20T11:02:00Z", "login_failed", "203.0.113.122"),
                _event("EVT-3", "2026-10-20T11:04:00Z", "login_failed", "203.0.113.122"),
                _event("EVT-4", "2026-10-20T11:06:00Z", "login_success", "203.0.113.122"),
            ],
        }
        result = analyze_incident(incident)
        self.assertEqual(result["classification"], "SUSPICIOUS")
        self.assertEqual(result["risk_score"], 55)
        self.assertEqual(result["severity"], "MEDIUM")
        rule_ids = [hit["rule_id"] for hit in result["rule_hits"]]
        self.assertIn("GB-RULE-001", rule_ids)
        self.assertIn("GB-RULE-003", rule_ids)

    def test_failure_burst_inside_default_window(self):
        incident = {
            "department": "Support",
            "known_ips": ["203.0.113.5"],
            "events": [
                _event("EVT-A", "2026-10-20T10:00:00Z", "login_failed", "203.0.113.5"),
                _event("EVT-B", "2026-10-20T10:10:00Z", "login_failed", "203.0.113.5"),
                _event("EVT-C", "2026-10-20T10:20:00Z", "login_failed", "203.0.113.5"),
            ],
        }
        result = analyze_incident(incident)
        self.assertEqual(DEFAULT_FAILURE_BURST_WINDOW_MINUTES, 30)
        self.assertEqual(result["classification"], "SUSPICIOUS")
        self.assertEqual(result["risk_score"], 30)
        self.assertEqual(result["severity"], "MEDIUM")

    def test_failures_outside_burst_window_are_insufficient_evidence(self):
        incident = {
            "department": "QA",
            "known_ips": ["203.0.113.129"],
            "events": [
                _event("EVT-1", "2026-10-21T08:00:00Z", "login_failed", "198.51.100.129"),
                _event("EVT-2", "2026-10-21T12:00:00Z", "login_failed", "198.51.100.129"),
                _event("EVT-3", "2026-10-21T16:00:00Z", "login_failed", "198.51.100.129"),
            ],
        }
        result = analyze_incident(incident)
        self.assertEqual(result["classification"], "INSUFFICIENT_EVIDENCE")
        self.assertEqual(result["risk_score"], 0)
        self.assertIsNone(result["severity"])
        self.assertTrue(any(hit["rule_id"] == "GB-RULE-006" for hit in result["rule_hits"]))
        self.assertFalse(any(hit["rule_id"] == "GB-RULE-001" for hit in result["rule_hits"]))

    def test_out_of_order_timestamps_use_chronology(self):
        incident = {
            "department": "QA",
            "known_ips": ["203.0.113.134"],
            "events": [
                _event("EVT-S", "2026-10-21T13:06:00Z", "login_success", "198.51.100.134"),
                _event("EVT-F3", "2026-10-21T13:04:00Z", "login_failed", "198.51.100.134"),
                _event("EVT-F2", "2026-10-21T13:02:00Z", "login_failed", "198.51.100.134"),
                _event("EVT-F1", "2026-10-21T13:00:00Z", "login_failed", "198.51.100.134"),
            ],
        }
        shuffled = analyze_incident(incident)
        chronological = analyze_incident(
            {
                **incident,
                "events": list(reversed(incident["events"])),
            }
        )
        self.assertEqual(shuffled["classification"], "SUSPICIOUS")
        self.assertEqual(shuffled["risk_score"], chronological["risk_score"])
        self.assertEqual(shuffled["classification"], chronological["classification"])
        self.assertIn("EVT-S", shuffled["evidence_ids"])

    def test_empty_ip_is_insufficient_evidence_not_unfamiliar(self):
        incident = {
            "department": "QA",
            "known_ips": [],
            "events": [
                _event("EVT-1", "2026-10-21T10:00:00Z", "login_success", ""),
            ],
        }
        result = analyze_incident(incident)
        self.assertEqual(result["classification"], "INSUFFICIENT_EVIDENCE")
        self.assertEqual(result["risk_score"], 0)
        self.assertIsNone(result["severity"])
        self.assertFalse(any(hit["rule_id"] == "GB-RULE-002" for hit in result["rule_hits"]))

    def test_overlapping_rules_do_not_double_count_failure_points(self):
        incident = {
            "department": "Engineering",
            "known_ips": ["203.0.113.10"],
            "events": [
                _event("EVT-1", "2026-10-21T09:00:00Z", "login_failed", "198.51.100.130"),
                _event("EVT-2", "2026-10-21T09:01:00Z", "login_failed", "198.51.100.130"),
                _event("EVT-3", "2026-10-21T09:02:00Z", "login_failed", "198.51.100.130"),
                _event("EVT-4", "2026-10-21T09:03:00Z", "login_success", "198.51.100.130"),
            ],
        }
        result = analyze_incident(incident)
        self.assertEqual(result["risk_score"], 70)
        self.assertLessEqual(result["risk_score"], 100)
        points_by_rule = {hit["rule_id"]: hit["points"] for hit in result["rule_hits"]}
        self.assertEqual(points_by_rule.get("GB-RULE-001"), 30)
        self.assertEqual(points_by_rule.get("GB-RULE-003"), 40)
        self.assertNotIn("GB-RULE-002", points_by_rule)

    def test_same_failure_burst_with_multiple_successes_scores_rule_003_once(self):
        incident = {
            "department": "Engineering",
            "known_ips": ["203.0.113.10"],
            "events": [
                _event("EVT-1", "2026-10-21T13:00:00Z", "login_failed", "198.51.100.50"),
                _event("EVT-2", "2026-10-21T13:01:00Z", "login_failed", "198.51.100.50"),
                _event("EVT-3", "2026-10-21T13:02:00Z", "login_failed", "198.51.100.50"),
                _event("EVT-4", "2026-10-21T13:03:00Z", "login_success", "198.51.100.50"),
                _event("EVT-5", "2026-10-21T13:04:00Z", "login_success", "198.51.100.50"),
                _event("EVT-6", "2026-10-21T13:05:00Z", "login_success", "198.51.100.50"),
            ],
        }
        result = analyze_incident(incident)
        rule_003_hits = [hit for hit in result["rule_hits"] if hit["rule_id"] == "GB-RULE-003"]
        self.assertEqual(len(rule_003_hits), 1)
        self.assertEqual(result["risk_score"], 70)  # 30 + 40, not 30 + 40*3
        self.assertEqual(result["classification"], "SUSPICIOUS")
        self.assertEqual(result["severity"], "HIGH")
        self.assertEqual(result["investigation_priority"], "HIGH")
        self.assertEqual(rule_003_hits[0]["points"], 40)
        for success_id in ("EVT-4", "EVT-5", "EVT-6"):
            self.assertIn(success_id, rule_003_hits[0]["evidence_ids"])
        self.assertEqual(
            sum(int(hit["points"]) for hit in result["rule_hits"] if hit["rule_id"] == "GB-RULE-003"),
            40,
        )

    def test_independent_failure_success_patterns_can_each_contribute(self):
        incident = {
            "department": "Engineering",
            "known_ips": ["203.0.113.10"],
            "events": [
                _event("EVT-A1", "2026-10-21T09:00:00Z", "login_failed", "198.51.100.1"),
                _event("EVT-A2", "2026-10-21T09:01:00Z", "login_failed", "198.51.100.1"),
                _event("EVT-A3", "2026-10-21T09:02:00Z", "login_failed", "198.51.100.1"),
                _event("EVT-A4", "2026-10-21T09:03:00Z", "login_success", "198.51.100.1"),
                _event("EVT-B1", "2026-10-21T10:00:00Z", "login_failed", "198.51.100.2"),
                _event("EVT-B2", "2026-10-21T10:01:00Z", "login_failed", "198.51.100.2"),
                _event("EVT-B3", "2026-10-21T10:02:00Z", "login_failed", "198.51.100.2"),
                _event("EVT-B4", "2026-10-21T10:03:00Z", "login_success", "198.51.100.2"),
            ],
        }
        result = analyze_incident(incident)
        rule_003_hits = [hit for hit in result["rule_hits"] if hit["rule_id"] == "GB-RULE-003"]
        self.assertEqual(len(rule_003_hits), 2)
        self.assertEqual(result["risk_score"], 100)  # capped: 30 + 40 + 40
        self.assertEqual(result["classification"], "SUSPICIOUS")
        self.assertEqual(result["severity"], "HIGH")
        evidence_sets = {frozenset(hit["evidence_ids"]) for hit in rule_003_hits}
        self.assertIn(frozenset({"EVT-A1", "EVT-A2", "EVT-A3", "EVT-A4"}), evidence_sets)
        self.assertIn(frozenset({"EVT-B1", "EVT-B2", "EVT-B3", "EVT-B4"}), evidence_sets)

    def test_finance_and_non_finance_identical_pattern_score_parity(self):
        events = [
            _event("EVT-1", "2026-10-21T12:00:00Z", "login_failed", "203.0.113.133"),
            _event("EVT-2", "2026-10-21T12:01:00Z", "login_failed", "203.0.113.133"),
            _event("EVT-3", "2026-10-21T12:02:00Z", "login_failed", "203.0.113.133"),
            _event("EVT-4", "2026-10-21T12:03:00Z", "login_success", "203.0.113.133"),
        ]
        qa = analyze_incident(
            {"department": "Quality Assurance", "known_ips": ["203.0.113.133"], "events": events}
        )
        finance = analyze_incident(
            {"department": "Finance", "known_ips": ["203.0.113.133"], "events": events}
        )
        self.assertEqual(qa["risk_score"], finance["risk_score"])
        self.assertEqual(qa["classification"], finance["classification"])
        self.assertEqual(qa["severity"], finance["severity"])
        self.assertFalse(any(hit["rule_id"] == "GB-RULE-004" for hit in finance["rule_hits"]))

    def test_risk_score_and_classification_remain_separate(self):
        insufficient = analyze_incident(self.incidents[1])
        self.assertEqual(insufficient["risk_score"], 0)
        self.assertEqual(insufficient["classification"], "INSUFFICIENT_EVIDENCE")
        self.assertNotEqual(insufficient["classification"], "NORMAL")

        normal = analyze_incident(self.incidents[2])
        self.assertEqual(normal["risk_score"], 0)
        self.assertEqual(normal["classification"], "NORMAL")
        self.assertIsNone(normal["severity"])

    def test_score_is_capped_at_100(self):
        # Many bursts are still capped; exercise the public contract.
        result = analyze_incident(self.incidents[0])
        self.assertLessEqual(result["risk_score"], 100)

    def test_configurable_burst_window_parameter(self):
        incident = {
            "department": "QA",
            "known_ips": ["203.0.113.1"],
            "events": [
                _event("EVT-1", "2026-10-21T08:00:00Z", "login_failed", "198.51.100.1"),
                _event("EVT-2", "2026-10-21T08:20:00Z", "login_failed", "198.51.100.1"),
                _event("EVT-3", "2026-10-21T08:40:00Z", "login_failed", "198.51.100.1"),
            ],
        }
        wide = analyze_incident(incident, failure_burst_window_minutes=45)
        narrow = analyze_incident(incident, failure_burst_window_minutes=15)
        self.assertEqual(wide["classification"], "SUSPICIOUS")
        self.assertEqual(narrow["classification"], "INSUFFICIENT_EVIDENCE")


@unittest.skipUnless(_HAS_SKLEARN, "scikit-learn is not installed in this environment")
class TestGuardBeePolicyRetrieval(unittest.TestCase):
    def setUp(self):
        self.policies = json.loads((ROOT / "data" / "policies.json").read_text(encoding="utf-8"))

    def test_tfidf_returns_ranked_policy_records(self):
        from retrieval import retrieve_policies

        matches = retrieve_policies("unfamiliar login IP Finance approval", self.policies, top_k=3)
        self.assertEqual(len(matches), 3)
        self.assertTrue(matches[0]["id"].startswith("POL-"))
        self.assertGreaterEqual(matches[0]["match_score"], matches[-1]["match_score"])

    def test_tfidf_returns_no_match_for_unrelated_or_empty_query(self):
        from retrieval import retrieve_policies

        self.assertEqual(retrieve_policies("quasar nebula", self.policies), [])
        self.assertEqual(retrieve_policies("", self.policies), [])
        self.assertEqual(retrieve_policies("login", []), [])

    def test_tfidf_threshold_can_exclude_weak_matches(self):
        from retrieval import retrieve_policies

        matches = retrieve_policies("unfamiliar login", self.policies, min_similarity=0.99)
        self.assertEqual(matches, [])


if __name__ == "__main__":
    unittest.main()
