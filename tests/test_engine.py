import importlib.util
import json
import unittest
from pathlib import Path

from engine import (
    DEFAULT_FAILURE_BURST_WINDOW_MINUTES,
    _priority_for,
    _severity_for_suspicious,
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
        self.assertEqual(result["risk_score"], 65)  # 20 burst + 5 speed + 15 success + 15 unfamiliar + 10 new country
        self.assertEqual(result["severity"], "HIGH")
        self.assertEqual(result["investigation_priority"], "HIGH")
        self.assertIn("EVT-006", result["evidence_ids"])
        points = {hit["rule_id"]: hit["points"] for hit in result["rule_hits"]}
        self.assertEqual(
            points, {"GB-RULE-001": 20, "GB-RULE-007": 5, "GB-RULE-003": 15, "GB-RULE-008": 15, "GB-RULE-010": 10}
        )
        self.assertNotIn("GB-RULE-004", points)
        # Unfamiliar success is covered by fail-then-success; do not stack RULE-002 points.
        self.assertNotIn("GB-RULE-002", points)

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
        # 15 burst + 3 speed + 15 success - 10 because every sign-in came from the known IP.
        self.assertEqual(result["risk_score"], 23)
        self.assertEqual(result["severity"], "LOW")
        rule_ids = [hit["rule_id"] for hit in result["rule_hits"]]
        self.assertIn("GB-RULE-001", rule_ids)
        self.assertIn("GB-RULE-003", rule_ids)
        self.assertIn("GB-RULE-013", rule_ids)

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
        self.assertEqual(result["risk_score"], 16)  # 15 for three failures + 1 for a slow 20-minute spread
        self.assertEqual(result["severity"], "LOW")

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
        self.assertEqual(result["risk_score"], 50)
        points_by_rule = {hit["rule_id"]: hit["points"] for hit in result["rule_hits"]}
        # Failures are scored once (RULE-001); RULE-003 and RULE-008 score only the sign-in.
        self.assertEqual(
            points_by_rule, {"GB-RULE-001": 15, "GB-RULE-007": 5, "GB-RULE-003": 15, "GB-RULE-008": 15}
        )

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
        self.assertEqual(result["risk_score"], 60)  # 15 + 5 + (15 + 5 + 5) + 15
        self.assertEqual(result["classification"], "SUSPICIOUS")
        self.assertEqual(result["severity"], "MEDIUM")
        self.assertEqual(result["investigation_priority"], "MEDIUM")
        self.assertEqual(rule_003_hits[0]["points"], 25)
        for success_id in ("EVT-4", "EVT-5", "EVT-6"):
            self.assertIn(success_id, rule_003_hits[0]["evidence_ids"])

    def test_independent_patterns_add_sign_ins_and_ips_without_double_counting(self):
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
        self.assertEqual(len(rule_003_hits), 1)
        self.assertEqual(
            set(rule_003_hits[0]["evidence_ids"]),
            {"EVT-A1", "EVT-A2", "EVT-A3", "EVT-A4", "EVT-B1", "EVT-B2", "EVT-B3", "EVT-B4"},
        )
        points = {hit["rule_id"]: hit["points"] for hit in result["rule_hits"]}
        self.assertEqual(points["GB-RULE-003"], 20)  # two sign-ins
        self.assertEqual(points["GB-RULE-009"], 4)  # two unfamiliar IPs
        self.assertEqual(result["risk_score"], 59)  # 15 + 5 + 20 + 15 + 4
        self.assertEqual(result["classification"], "SUSPICIOUS")
        self.assertEqual(result["severity"], "MEDIUM")

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
        events = [
            _event("EVT-K", "2026-10-21T01:00:00Z", "login_success", "203.0.113.9", "India"),
            *[_event(f"EVT-F{n}", f"2026-10-21T01:{10 + n // 4:02d}:{n % 4 * 15:02d}Z", "login_failed",
                     "198.51.100.9", "Brazil") for n in range(8)],
            _event("EVT-X", "2026-10-21T01:12:00Z", "login_failed", "192.0.2.9", "Germany"),
            _event("EVT-Y", "2026-10-21T01:12:30Z", "login_failed", "192.0.2.10", "Germany"),
            *[_event(f"EVT-S{n}", f"2026-10-21T01:{13 + n:02d}:00Z", "login_success", "198.51.100.9", "Brazil")
              for n in range(3)],
        ]
        result = analyze_incident({"department": "Sales", "known_ips": ["203.0.113.9"], "events": events})
        self.assertGreater(sum(hit["points"] for hit in result["rule_hits"]), 100)
        self.assertEqual(result["risk_score"], 100)
        self.assertEqual(result["severity"], "CRITICAL")
        self.assertEqual(result["investigation_priority"], "HIGH")

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


def _burst(ip, minutes, count=3, start="2026-10-22T10:00:00", country="Unknown"):
    """``count`` failures from ``ip`` spread evenly over ``minutes``, starting at ``start`` (UTC)."""
    from datetime import datetime, timedelta

    first = datetime.fromisoformat(start)
    step = timedelta(minutes=minutes / max(count - 1, 1))
    return [
        _event(f"EVT-F{n}", (first + step * n).strftime("%Y-%m-%dT%H:%M:%SZ"), "login_failed", ip, country)
        for n in range(count)
    ]


def _points(result):
    return {hit["rule_id"]: hit["points"] for hit in result["rule_hits"]}


class TestDynamicScoring(unittest.TestCase):
    """Each signal of the v2.3 event-based score, the severity bands, and the bundled spread."""

    UNFAMILIAR = "198.51.100.20"
    KNOWN = "203.0.113.20"

    def score(self, events, **incident):
        return analyze_incident({"department": "QA", "known_ips": [self.KNOWN], "events": events, **incident})

    def test_severity_band_edges(self):
        for score, severity in ((0, "LOW"), (14, "LOW"), (15, "LOW"), (39, "LOW"), (40, "MEDIUM"), (64, "MEDIUM"),
                                (65, "HIGH"), (84, "HIGH"), (85, "CRITICAL"), (100, "CRITICAL")):
            with self.subTest(score=score):
                self.assertEqual(_severity_for_suspicious(score), severity)

    def test_priority_follows_severity(self):
        expected = {"CRITICAL": "HIGH", "HIGH": "HIGH", "MEDIUM": "MEDIUM", "LOW": "LOW"}
        for severity, priority in expected.items():
            with self.subTest(severity=severity):
                self.assertEqual(_priority_for("SUSPICIOUS", severity), priority)

    def test_burst_points_grow_per_failure_up_to_30(self):
        for count, points in ((3, 15), (4, 20), (6, 30), (9, 30)):
            with self.subTest(failures=count):
                self.assertEqual(_points(self.score(_burst(self.UNFAMILIAR, 20, count)))["GB-RULE-001"], points)

    def test_fast_burst_scores_more_than_slow_burst(self):
        fast = self.score(_burst(self.UNFAMILIAR, 2))
        slow = self.score(_burst(self.UNFAMILIAR, 25))
        self.assertEqual(_points(fast)["GB-RULE-007"], 5)  # one failure a minute
        self.assertNotIn("GB-RULE-007", _points(slow))  # 0.08 a minute rounds to nothing
        self.assertGreater(fast["risk_score"], slow["risk_score"])
        self.assertEqual(_points(self.score(_burst(self.UNFAMILIAR, 1, count=6)))["GB-RULE-007"], 10)  # capped

    def test_each_extra_sign_in_adds_five_up_to_25(self):
        for successes, points in ((1, 15), (2, 20), (3, 25), (4, 25)):
            events = _burst(self.UNFAMILIAR, 2) + [
                _event(f"EVT-S{n}", f"2026-10-22T10:0{3 + n}:00Z", "login_success", self.UNFAMILIAR)
                for n in range(successes)
            ]
            with self.subTest(successes=successes):
                points_by_rule = _points(self.score(events))
                self.assertEqual(points_by_rule["GB-RULE-003"], points)
                self.assertEqual(points_by_rule["GB-RULE-008"], 15)

    def test_new_country_needs_a_known_home_and_a_located_sign_in(self):
        success = _event("EVT-S", "2026-10-22T10:03:00Z", "login_success", self.UNFAMILIAR, "Nigeria")
        events = _burst(self.UNFAMILIAR, 2, country="Nigeria") + [success]
        self.assertEqual(_points(self.score(events, home_country="India"))["GB-RULE-010"], 10)
        self.assertNotIn("GB-RULE-010", _points(self.score(events)))  # no home to compare with
        unknown = dict(success, country="Unknown")
        self.assertNotIn("GB-RULE-010", _points(self.score(events[:-1] + [unknown], home_country="India")))

    def test_impossible_travel_within_three_hours(self):
        home = _event("EVT-H", "2026-10-22T08:30:00Z", "login_success", self.KNOWN, "India")
        attack = _burst(self.UNFAMILIAR, 2, country="Brazil") + [
            _event("EVT-S", "2026-10-22T10:03:00Z", "login_success", self.UNFAMILIAR, "Brazil")
        ]
        travel = self.score([home] + attack)
        self.assertEqual(_points(travel)["GB-RULE-011"], 15)
        self.assertEqual(travel["rule_hits"][-1]["evidence_ids"], ["EVT-H", "EVT-S"])
        earlier = dict(home, time_utc="2026-10-22T06:00:00Z")  # 4 hours apart: travel is possible
        self.assertNotIn("GB-RULE-011", _points(self.score([earlier] + attack)))

    def test_off_hours_sign_in_adds_four(self):
        night = _burst(self.UNFAMILIAR, 2, start="2026-10-22T02:00:00") + [
            _event("EVT-S", "2026-10-22T02:03:00Z", "login_success", self.UNFAMILIAR)
        ]
        day = _burst(self.UNFAMILIAR, 2) + [_event("EVT-S", "2026-10-22T10:03:00Z", "login_success", self.UNFAMILIAR)]
        self.assertEqual(_points(self.score(night))["GB-RULE-012"], 4)
        self.assertEqual(self.score(night)["risk_score"] - self.score(day)["risk_score"], 4)

    def test_known_only_sign_ins_lower_the_score_but_stay_suspicious(self):
        events = _burst(self.KNOWN, 2, country="India") + [
            _event("EVT-S", "2026-10-22T10:03:00Z", "login_success", self.KNOWN, "India")
        ]
        result = self.score(events)
        self.assertEqual(_points(result)["GB-RULE-013"], -10)
        self.assertEqual(result["risk_score"], 25)  # 15 + 5 + 15 - 10
        self.assertEqual(result["classification"], "SUSPICIOUS")

    def test_context_signals_never_make_activity_suspicious(self):
        # A night-time sign-in from a new country and a second IP, with no failure burst.
        events = [
            _event("EVT-1", "2026-10-22T01:00:00Z", "login_success", self.KNOWN, "India"),
            _event("EVT-2", "2026-10-22T02:00:00Z", "login_success", self.UNFAMILIAR, "Brazil"),
            _event("EVT-3", "2026-10-22T02:05:00Z", "login_failed", "192.0.2.20", "Germany"),
        ]
        result = self.score(events)
        self.assertEqual(result["classification"], "INSUFFICIENT_EVIDENCE")
        self.assertEqual(result["risk_score"], 0)
        self.assertEqual(set(_points(result)), {"GB-RULE-002"})

    def test_rule_points_add_up_to_every_bundled_score(self):
        incidents = json.loads((ROOT / "data" / "incidents.json").read_text(encoding="utf-8"))
        for incident in incidents:
            result = analyze_incident(incident)
            with self.subTest(incident=incident["id"]):
                total = sum(hit["points"] for hit in result["rule_hits"])
                self.assertEqual(result["risk_score"], max(0, min(total, 100)))

    def test_bundled_scores_spread_across_every_severity(self):
        incidents = json.loads((ROOT / "data" / "incidents.json").read_text(encoding="utf-8"))
        suspicious = [r for r in map(analyze_incident, incidents) if r["classification"] == "SUSPICIOUS"]
        scores = [result["risk_score"] for result in suspicious]
        self.assertEqual(len(scores), len(set(scores)), "two suspicious incidents share a score")
        self.assertEqual({result["severity"] for result in suspicious}, {"CRITICAL", "HIGH", "MEDIUM", "LOW"})


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
