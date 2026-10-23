import unittest
from types import SimpleNamespace
from unittest.mock import patch

from ai_client import AIReportError, generate_report, validate_report_citations


class TestReportValidation(unittest.TestCase):
    def test_accepts_report_with_supplied_event_and_policy_citations(self):
        usable, _ = validate_report_citations("Evidence EVT-006 supports POL-001.", ["EVT-006"], ["POL-001"])
        self.assertTrue(usable)

    def test_rejects_fabricated_or_stale_event_ids(self):
        usable, reason = validate_report_citations(
            "Evidence EVT-006 and EVT-102 support POL-001.", ["EVT-006"], ["POL-001"]
        )
        self.assertFalse(usable)
        self.assertIn("EVT-102", reason)

    def test_rejects_policy_that_was_not_retrieved(self):
        usable, reason = validate_report_citations(
            "Evidence EVT-006 supports POL-004.", ["EVT-006"], ["POL-001"]
        )
        self.assertFalse(usable)
        self.assertIn("POL-004", reason)

    def test_rejects_missing_policy_or_event_citation(self):
        usable, _ = validate_report_citations("Evidence EVT-006 was observed.", ["EVT-006"], ["POL-001"])
        self.assertFalse(usable)

    def test_rejects_uncited_report(self):
        usable, reason = validate_report_citations("A generic recommendation.", ["EVT-006"], ["POL-001"])
        self.assertFalse(usable)
        self.assertIn("must cite", reason)

    def test_missing_key_is_a_safe_error(self):
        with self.assertRaises(AIReportError):
            generate_report("", {}, {}, [])

    @patch("ai_client.OpenAI")
    def test_provider_failure_is_a_safe_error(self, client_class):
        client_class.return_value.chat.completions.create.side_effect = RuntimeError("network")
        with self.assertRaises(AIReportError):
            generate_report("test-key", {}, {}, [])

    @patch("ai_client.OpenAI")
    def test_empty_or_malformed_provider_response_is_a_safe_error(self, client_class):
        client_class.return_value.chat.completions.create.return_value = SimpleNamespace(choices=[])
        with self.assertRaises(AIReportError):
            generate_report("test-key", {}, {}, [])


if __name__ == "__main__":
    unittest.main()
