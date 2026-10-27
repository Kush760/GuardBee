import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from ai_client import (
    AIReportError,
    generate_report,
    validate_report_citations,
)


class TestReportValidation(unittest.TestCase):
    def test_accepts_report_with_supplied_event_and_policy_citations(self):
        usable, _ = validate_report_citations(
            "Evidence EVT-006 supports POL-001.", ["EVT-006"], ["POL-001"]
        )
        self.assertTrue(usable)

    def test_accepts_unicode_hyphen_citations_from_model_output(self):
        # Live Nemotron responses have used U+2011 in EVT‑* / POL‑* tokens.
        report = "Evidence EVT\u2011006 supports POL\u2011001 for investigation."
        usable, reason = validate_report_citations(
            report, ["EVT-006"], ["POL-001"], classification="SUSPICIOUS"
        )
        self.assertTrue(usable, reason)

    def test_accepts_adjacent_event_ids_without_treating_range_as_unknown(self):
        report = (
            "Failures EVT-002-EVT-005 then success EVT-006 support POL-001."
        )
        usable, reason = validate_report_citations(
            report,
            ["EVT-002", "EVT-003", "EVT-004", "EVT-005", "EVT-006"],
            ["POL-001"],
            classification="SUSPICIOUS",
        )
        self.assertTrue(usable, reason)

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
        usable, _ = validate_report_citations(
            "Evidence EVT-006 was observed.", ["EVT-006"], ["POL-001"]
        )
        self.assertFalse(usable)

    def test_rejects_uncited_report(self):
        usable, reason = validate_report_citations(
            "A generic recommendation.", ["EVT-006"], ["POL-001"]
        )
        self.assertFalse(usable)
        self.assertIn("must cite", reason)

    def test_rejects_confirmed_compromise_claims(self):
        usable, reason = validate_report_citations(
            "EVT-006 and POL-001 show confirmed compromise of the account.",
            ["EVT-006"],
            ["POL-001"],
            classification="SUSPICIOUS",
        )
        self.assertFalse(usable)
        self.assertIn("confirmed compromise", reason)

    def test_rejects_overstated_certainty_for_insufficient_classification(self):
        usable, reason = validate_report_citations(
            "EVT-102 and POL-001 show confirmed suspicious activity.",
            ["EVT-102"],
            ["POL-001"],
            classification="INSUFFICIENT_EVIDENCE",
        )
        self.assertFalse(usable)
        self.assertIn("overstates certainty", reason)

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
        client_class.return_value.chat.completions.create.return_value = SimpleNamespace(
            choices=[]
        )
        with self.assertRaises(AIReportError):
            generate_report("test-key", {}, {}, [])

    @patch("ai_client.OpenAI")
    def test_prompt_grounds_deterministic_classification_and_priority(self, client_class):
        create = client_class.return_value.chat.completions.create
        create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="See EVT-1 and POL-001."))]
        )
        analysis = {
            "classification": "INSUFFICIENT_EVIDENCE",
            "risk_score": 0,
            "severity": None,
            "investigation_priority": "LOW",
            "rule_hits": [
                {
                    "rule_id": "GB-RULE-002",
                    "flag": "Successful login from an unfamiliar IP without supporting failure evidence",
                    "points": 0,
                    "evidence_ids": ["EVT-1"],
                }
            ],
            "flags": ["Successful login from an unfamiliar IP without supporting failure evidence"],
            "evidence_ids": ["EVT-1"],
            "suggested_action": "gather additional context",
        }
        policies = [
            {
                "id": "POL-001",
                "title": "Unusual login",
                "text": "Investigate unfamiliar IPs.",
                "categories": ["unfamiliar_ip"],
                "investigation_guidance": "Do not claim compromise.",
                "match_score": 0.42,
            }
        ]
        report = generate_report(
            "test-key",
            {"id": "INC-1", "events": [{"id": "EVT-1"}]},
            analysis,
            policies,
        )
        self.assertEqual(report, "See EVT-1 and POL-001.")
        kwargs = create.call_args.kwargs
        system = kwargs["messages"][0]["content"]
        user_payload = json.loads(kwargs["messages"][1]["content"])
        self.assertIn("classification", system.lower())
        self.assertIn("confirmed compromise", system.lower())
        self.assertIn("unfamiliar IP alone", system)
        grounded = user_payload["deterministic_rule_analysis"]
        self.assertEqual(grounded["classification"], "INSUFFICIENT_EVIDENCE")
        self.assertEqual(grounded["investigation_priority"], "LOW")
        self.assertEqual(grounded["risk_score"], 0)
        self.assertEqual(grounded["evidence_ids"], ["EVT-1"])
        self.assertEqual(
            user_payload["retrieved_company_policies"][0]["investigation_guidance"],
            "Do not claim compromise.",
        )
        self.assertTrue(
            user_payload["grounding_instructions"]["never_claim_confirmed_compromise"]
        )


if __name__ == "__main__":
    unittest.main()
