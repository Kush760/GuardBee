"""MVP scenario coverage from dedicated fixtures (production JSON stays metadata-free)."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from data_loader import DataValidationError, partition_incidents, validate_incidents
from engine import analyze_incident

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"


class TestScenarioFixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.incidents = json.loads(
            (FIXTURES / "scenario_incidents.json").read_text(encoding="utf-8")
        )
        cls.expectations = json.loads(
            (FIXTURES / "scenario_expectations.json").read_text(encoding="utf-8")
        )
        cls.by_id = {incident["id"]: incident for incident in cls.incidents}
        cls.production = json.loads(
            (ROOT / "data" / "incidents.json").read_text(encoding="utf-8")
        )

    def test_fixture_and_production_schemas_are_valid(self):
        validate_incidents(self.incidents)
        validate_incidents(self.production)
        for incident in self.incidents + self.production:
            self.assertNotIn("test_metadata", incident)
            self.assertNotIn("scenario_context", incident)
            for event in incident["events"]:
                self.assertNotIn("evidence_context", event)

    def test_fixture_classifications_match_engine(self):
        for expectation in self.expectations:
            if not expectation["in_production"]:
                continue
            incident = self.by_id[expectation["id"]]
            result = analyze_incident(incident)
            self.assertEqual(
                result["classification"],
                expectation["expected_classification"],
                msg=f"{expectation['id']} ({expectation['scenario_type']})",
            )

    def test_required_mvp_scenario_types_are_present(self):
        types = {item["scenario_type"] for item in self.expectations}
        required = {
            "repeated_failures_then_unfamiliar_ip_success",
            "single_success_from_unfamiliar_ip",
            "one_failure_then_success_from_known_ip",
            "repeated_successes_from_known_ip",
            "failures_outside_burst_window",
            "overlapping_rule_evidence",
            "incomplete_evidence",
            "known_ip_not_automatically_safe",
            "department_independent_scoring",
            "input_events_out_of_order",
        }
        self.assertTrue(required.issubset(types), msg=f"missing {required - types}")

    def test_department_independent_scoring_parity(self):
        qa = analyze_incident(self.by_id["INC-1012"])
        finance = analyze_incident(self.by_id["INC-1013"])
        self.assertEqual(qa["classification"], "SUSPICIOUS")
        self.assertEqual(finance["classification"], "SUSPICIOUS")
        self.assertEqual(qa["risk_score"], finance["risk_score"])
        self.assertEqual(
            [hit["rule_id"] for hit in qa["rule_hits"]],
            [hit["rule_id"] for hit in finance["rule_hits"]],
        )

    def test_chronology_fixture_ignores_array_order(self):
        incident = self.by_id["INC-1014"]
        times = [event["time_utc"] for event in incident["events"]]
        self.assertNotEqual(times, sorted(times))
        result = analyze_incident(incident)
        # Proposal INC-1014 has only two failures; after timestamp sort the engine
        # correctly yields INSUFFICIENT_EVIDENCE (GB-RULE-002), not SUSPICIOUS.
        self.assertEqual(result["classification"], "INSUFFICIENT_EVIDENCE")
        self.assertIn("GB-RULE-002", [hit["rule_id"] for hit in result["rule_hits"]])
        self.assertNotIn("GB-RULE-003", [hit["rule_id"] for hit in result["rule_hits"]])

    def test_overlapping_evidence_does_not_exceed_cap(self):
        result = analyze_incident(self.by_id["INC-1010"])
        self.assertEqual(result["classification"], "SUSPICIOUS")
        self.assertLessEqual(result["risk_score"], 100)
        failure_point_total = sum(
            int(hit["points"])
            for hit in result["rule_hits"]
            if hit["rule_id"] == "GB-RULE-001"
        )
        # Dynamic scoring: 5 points per failure in the densest burst (INC-1010 has 3 → 15), capped at 30.
        self.assertEqual(failure_point_total, 15)
        self.assertLessEqual(failure_point_total, 30)

    def test_incomplete_ip_loader_and_engine(self):
        incomplete = json.loads(
            (FIXTURES / "incomplete_ip_incident.json").read_text(encoding="utf-8")
        )
        valid, errors = partition_incidents([incomplete])
        self.assertEqual(valid, [])
        self.assertEqual(len(errors), 1)
        self.assertIn("non-empty string", errors[0])
        with self.assertRaises(DataValidationError):
            validate_incidents([incomplete])
        result = analyze_incident(incomplete)
        self.assertEqual(result["classification"], "INSUFFICIENT_EVIDENCE")
        self.assertEqual(result["risk_score"], 0)
        self.assertTrue(any("missing or empty source IP" in flag for flag in result["flags"]))

    def test_production_includes_fixture_runtime_ids(self):
        production_ids = {incident["id"] for incident in self.production}
        for expectation in self.expectations:
            if expectation["in_production"]:
                self.assertIn(expectation["id"], production_ids)
            else:
                self.assertNotIn(expectation["id"], production_ids)


if __name__ == "__main__":
    unittest.main()
