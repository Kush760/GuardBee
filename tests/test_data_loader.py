import json
import unittest
from pathlib import Path
from unittest.mock import patch

from data_loader import DataValidationError, load_incidents, validate_incidents, validate_policies

ROOT = Path(__file__).resolve().parents[1]


class TestDataValidation(unittest.TestCase):
    def test_existing_incident_data_is_valid(self):
        incidents = load_incidents(ROOT / "data" / "incidents.json")
        self.assertEqual(len(incidents), 16)

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
            "events": [{"id": "EVT-X", "time_utc": "2026-01-01T00:00:00Z", "type": "other", "ip": "203.0.113.1", "country": "x"}],
        }
        with self.assertRaisesRegex(DataValidationError, "type"):
            validate_incidents([invalid_incident])
        with self.assertRaisesRegex(DataValidationError, "non-empty"):
            validate_policies([])

    def test_optional_location_fields_are_not_schema_validated(self):
        """data_loader requires event country/ip/etc.; home_city/home_country/city are optional and unchecked."""
        incident = {
            "id": "INC-X",
            "title": "x",
            "account": "x@example.test",
            "department": "x",
            "home_city": "Pune",
            "home_country": "India",
            "known_ips": [],
            "events": [
                {"id": "EVT-X", "time_utc": "2026-01-01T00:00:00Z", "type": "login_success", "ip": "203.0.113.1",
                 "country": "India", "city": "Pune"}
            ],
        }
        self.assertEqual(validate_incidents([incident]), [incident])
        # Blank optional enrichment must still validate under the current loader contract.
        for target, field in ((incident, "home_country"), (incident["events"][0], "city")):
            with self.subTest(field=field):
                relaxed = json.loads(json.dumps(incident))
                (relaxed if target is incident else relaxed["events"][0])[field] = "  "
                self.assertEqual(validate_incidents([relaxed]), [relaxed])

    def test_malformed_json_is_rejected(self):
        with patch.object(Path, "read_text", return_value="{"):
            with self.assertRaisesRegex(DataValidationError, "not valid JSON"):
                load_incidents(Path("invalid.json"))

    def test_missing_file_is_rejected(self):
        with self.assertRaisesRegex(DataValidationError, "Could not read"):
            load_incidents(Path("does-not-exist.json"))

    def test_policy_requires_text(self):
        with self.assertRaisesRegex(DataValidationError, "text"):
            validate_policies([{"id": "POL-X", "title": "x"}])
