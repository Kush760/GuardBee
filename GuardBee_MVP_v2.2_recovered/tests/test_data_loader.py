import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from data_loader import (
    DataValidationError,
    IncidentPartitionResult,
    IncidentValidationIssue,
    load_incidents,
    load_incidents_partitioned,
    partition_incidents,
    validate_incidents,
    validate_policies,
)
from engine import analyze_incident

ROOT = Path(__file__).resolve().parents[1]


def _valid_incident(incident_id: str = "INC-OK", event_id: str = "EVT-OK") -> dict:
    return {
        "id": incident_id,
        "title": "Valid synthetic incident",
        "account": "user@example.test",
        "department": "Support",
        "known_ips": ["203.0.113.1"],
        "events": [
            {
                "id": event_id,
                "time_utc": "2026-01-01T00:00:00Z",
                "type": "login_success",
                "ip": "203.0.113.1",
                "country": "India",
            }
        ],
    }


class TestDataValidation(unittest.TestCase):
    def test_existing_incident_data_is_valid(self):
        incidents = load_incidents(ROOT / "data" / "incidents.json")
        self.assertEqual(len(incidents), 13)
        ids = {incident["id"] for incident in incidents}
        self.assertTrue({"INC-1001", "INC-1002", "INC-1003"}.issubset(ids))
        self.assertNotIn("INC-1011", ids)  # empty-IP case stays fixture-only
        for incident in incidents:
            self.assertNotIn("test_metadata", incident)

    def test_missing_required_incident_field_is_rejected(self):
        with self.assertRaisesRegex(DataValidationError, "account"):
            validate_incidents(
                [{"id": "INC-X", "title": "x", "department": "x", "known_ips": [], "events": []}]
            )

    def test_invalid_event_type_and_empty_policy_data_are_rejected(self):
        invalid_incident = {
            "id": "INC-X",
            "title": "x",
            "account": "x@example.test",
            "department": "x",
            "known_ips": [],
            "events": [
                {
                    "id": "EVT-X",
                    "time_utc": "2026-01-01T00:00:00Z",
                    "type": "other",
                    "ip": "203.0.113.1",
                    "country": "x",
                }
            ],
        }
        with self.assertRaisesRegex(DataValidationError, "type"):
            validate_incidents([invalid_incident])
        with self.assertRaisesRegex(DataValidationError, "non-empty"):
            validate_policies([])

    def test_malformed_json_is_rejected(self):
        with patch.object(Path, "read_text", return_value="{"):
            with self.assertRaisesRegex(DataValidationError, "not valid JSON"):
                load_incidents(Path("invalid.json"))
            with self.assertRaisesRegex(DataValidationError, "not valid JSON"):
                load_incidents_partitioned(Path("invalid.json"))

    def test_missing_file_is_rejected(self):
        with self.assertRaisesRegex(DataValidationError, "Could not read"):
            load_incidents(Path("does-not-exist.json"))
        with self.assertRaisesRegex(DataValidationError, "Could not read"):
            load_incidents_partitioned(Path("does-not-exist.json"))

    def test_empty_collection_is_rejected_by_partition_and_fail_closed(self):
        with self.assertRaisesRegex(DataValidationError, "non-empty JSON array"):
            partition_incidents([])
        with self.assertRaisesRegex(DataValidationError, "non-empty JSON array"):
            validate_incidents([])

    def test_policy_requires_text(self):
        with self.assertRaisesRegex(DataValidationError, "text"):
            validate_policies([{"id": "POL-X", "title": "x"}])

    def test_policy_optional_enrichment_fields_are_accepted(self):
        policies = validate_policies(
            [
                {
                    "id": "POL-OK",
                    "title": "Login guidance",
                    "text": "Investigate carefully.",
                    "description": "Short summary",
                    "categories": ["authentication"],
                    "conditions": "Unfamiliar IP present",
                    "investigation_guidance": "Cite EVT and POL IDs.",
                }
            ]
        )
        self.assertEqual(policies[0]["categories"], ["authentication"])

    def test_policy_optional_fields_may_be_omitted(self):
        policies = validate_policies(
            [{"id": "POL-MIN", "title": "Minimal", "text": "Enough for MVP retrieval."}]
        )
        self.assertEqual(policies[0]["id"], "POL-MIN")

    def test_policy_invalid_optional_categories_are_rejected(self):
        with self.assertRaisesRegex(DataValidationError, "categories"):
            validate_policies(
                [
                    {
                        "id": "POL-BAD",
                        "title": "x",
                        "text": "y",
                        "categories": [""],
                    }
                ]
            )

    def test_production_policies_load_with_enrichment(self):
        from data_loader import load_policies

        policies = load_policies(ROOT / "data" / "policies.json")
        self.assertGreaterEqual(len(policies), 4)
        self.assertTrue(all("investigation_guidance" in policy for policy in policies))

    def test_empty_ip_is_rejected_explicitly(self):
        incident = _valid_incident()
        incident["events"][0]["ip"] = ""
        with self.assertRaisesRegex(DataValidationError, "empty IP"):
            validate_incidents([incident])

    def test_missing_ip_field_is_rejected(self):
        incident = _valid_incident()
        del incident["events"][0]["ip"]
        with self.assertRaisesRegex(DataValidationError, r"\.ip must be a non-empty string"):
            validate_incidents([incident])

    def test_partition_keeps_valid_and_reports_invalid(self):
        good = _valid_incident("INC-GOOD", "EVT-GOOD")
        bad = _valid_incident("INC-BAD", "EVT-BAD")
        bad["events"][0]["ip"] = "   "
        result = partition_incidents([good, bad])
        self.assertIsInstance(result, IncidentPartitionResult)
        self.assertEqual([item["id"] for item in result.valid], ["INC-GOOD"])
        self.assertEqual(len(result.issues), 1)
        self.assertEqual(result.issues[0].index, 1)
        self.assertEqual(result.issues[0].incident_id, "INC-BAD")
        self.assertIn("empty IP", result.issues[0].message)
        valid, errors = result
        self.assertEqual(valid[0]["id"], "INC-GOOD")
        self.assertIn("INC-BAD", errors[0])

    def test_partition_reports_multiple_invalid_records_explicitly(self):
        good = _valid_incident("INC-GOOD", "EVT-GOOD")
        missing_account = {
            "id": "INC-NO-ACCOUNT",
            "title": "x",
            "department": "x",
            "known_ips": [],
            "events": [],
        }
        empty_ip = _valid_incident("INC-EMPTY-IP", "EVT-EMPTY")
        empty_ip["events"][0]["ip"] = ""
        result = partition_incidents([missing_account, good, empty_ip])
        self.assertEqual([item["id"] for item in result.valid], ["INC-GOOD"])
        self.assertEqual(len(result.issues), 2)
        self.assertEqual({issue.index for issue in result.issues}, {0, 2})
        self.assertTrue(any(issue.incident_id == "INC-NO-ACCOUNT" for issue in result.issues))
        self.assertTrue(any(issue.incident_id == "INC-EMPTY-IP" for issue in result.issues))

    def test_partition_reports_duplicate_incident_ids(self):
        first = _valid_incident("INC-DUP", "EVT-1")
        second = _valid_incident("INC-DUP", "EVT-2")
        result = partition_incidents([first, second])
        self.assertEqual(len(result.valid), 1)
        self.assertEqual(result.valid[0]["events"][0]["id"], "EVT-1")
        self.assertEqual(len(result.issues), 1)
        self.assertIn("duplicates incident id", result.issues[0].message)
        self.assertEqual(result.issues[0].incident_id, "INC-DUP")

    def test_partition_reports_duplicate_event_ids_within_incident(self):
        incident = _valid_incident("INC-EVT-DUP", "EVT-SAME")
        incident["events"].append(
            {
                "id": "EVT-SAME",
                "time_utc": "2026-01-01T01:00:00Z",
                "type": "login_failed",
                "ip": "203.0.113.1",
                "country": "India",
            }
        )
        result = partition_incidents([incident])
        self.assertEqual(result.valid, [])
        self.assertEqual(len(result.issues), 1)
        self.assertIn("duplicate id", result.issues[0].message)

    def test_fail_closed_validate_still_rejects_mixed_collections(self):
        good = _valid_incident("INC-GOOD", "EVT-GOOD")
        bad = _valid_incident("INC-BAD", "EVT-BAD")
        bad["events"][0]["ip"] = ""
        with self.assertRaises(DataValidationError):
            validate_incidents([good, bad])

    def test_partition_results_are_deterministic_across_calls(self):
        payload = [
            _valid_incident("INC-A", "EVT-A"),
            {"id": "INC-B", "title": "x", "department": "x", "known_ips": [], "events": []},
            _valid_incident("INC-C", "EVT-C"),
        ]
        first = partition_incidents(payload)
        second = partition_incidents(payload)
        self.assertEqual([item["id"] for item in first.valid], [item["id"] for item in second.valid])
        self.assertEqual(
            [(issue.index, issue.message, issue.incident_id) for issue in first.issues],
            [(issue.index, issue.message, issue.incident_id) for issue in second.issues],
        )

    def test_invalid_records_never_reach_detection_engine(self):
        good = _valid_incident("INC-GOOD", "EVT-GOOD")
        bad = _valid_incident("INC-BAD", "EVT-BAD")
        bad["events"][0]["ip"] = ""
        result = partition_incidents([bad, good])
        self.assertEqual([item["id"] for item in result.valid], ["INC-GOOD"])
        analyses = {
            incident["id"]: analyze_incident(incident) for incident in result.valid
        }
        self.assertIn("INC-GOOD", analyses)
        self.assertNotIn("INC-BAD", analyses)
        self.assertEqual(analyses["INC-GOOD"]["classification"], "NORMAL")

    def test_load_incidents_partitioned_from_file(self):
        good = _valid_incident("INC-FILE-GOOD", "EVT-FILE-GOOD")
        bad = _valid_incident("INC-FILE-BAD", "EVT-FILE-BAD")
        bad["events"][0]["type"] = "not-a-login"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "mixed.json"
            path.write_text(
                __import__("json").dumps([bad, good]),
                encoding="utf-8",
            )
            result = load_incidents_partitioned(path)
            self.assertEqual([item["id"] for item in result.valid], ["INC-FILE-GOOD"])
            self.assertEqual(len(result.issues), 1)
            self.assertIsInstance(result.issues[0], IncidentValidationIssue)
            with self.assertRaises(DataValidationError):
                load_incidents(path)


if __name__ == "__main__":
    unittest.main()
