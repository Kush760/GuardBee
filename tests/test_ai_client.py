import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import httpx
from openai import OpenAI

import ai_client
from ai_client import AIReportError, extract_citation_ids, generate_report, validate_report_citations

FAKE_KEY = "test-only-key-not-a-secret-7f3a"


def chat_completion(content, finish_reason="stop"):
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 0,
        "model": "test-model",
        "choices": [
            {"index": 0, "finish_reason": finish_reason, "message": {"role": "assistant", "content": content}}
        ],
    }


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

    def test_accepts_lowercase_form_of_allowed_ids(self):
        usable, _ = validate_report_citations("Evidence evt-006 supports pol-001.", ["EVT-006"], ["POL-001"])
        self.assertTrue(usable)

    def test_rejects_lowercase_fabricated_ids(self):
        usable, reason = validate_report_citations(
            "Evidence EVT-006 supports POL-001 and evt-999.", ["EVT-006"], ["POL-001"]
        )
        self.assertFalse(usable)
        self.assertIn("evt-999", reason)

    def test_rejects_ids_glued_to_letter_or_underscore_prefix(self):
        for text in ("_EVT-999", "xPOL-009", "x_EVT-006"):
            with self.subTest(text=text):
                usable, reason = validate_report_citations(
                    f"Evidence EVT-006 supports POL-001 and {text}.", ["EVT-006"], ["POL-001"]
                )
                self.assertFalse(usable)
                self.assertIn("malformed", reason)

    def test_rejects_ids_written_with_unicode_dashes(self):
        for dash in ("\u2010", "\u2011", "\u2013", "\u2014", "\u2212"):
            with self.subTest(dash=ascii(dash)):
                usable, reason = validate_report_citations(
                    f"Evidence EVT-006 supports POL-001 and EVT{dash}999.", ["EVT-006"], ["POL-001"]
                )
                self.assertFalse(usable)
                self.assertIn("malformed", reason)

    def test_unicode_dash_form_of_allowed_id_does_not_count_as_citation(self):
        usable, _ = validate_report_citations("Evidence EVT\u2011006 supports POL-001.", ["EVT-006"], ["POL-001"])
        self.assertFalse(usable)

    def test_rejects_ids_with_trailing_underscore_suffix(self):
        usable, reason = validate_report_citations(
            "Evidence EVT-006 supports POL-001 and EVT-999_x.", ["EVT-006"], ["POL-001"]
        )
        self.assertFalse(usable)
        self.assertIn("EVT-999_x", reason)

    def test_policy_id_cannot_satisfy_event_requirement(self):
        usable, _ = validate_report_citations("Guidance POL-001 and POL-002.", ["EVT-006"], ["POL-001", "POL-002"])
        self.assertFalse(usable)

    def test_extract_citation_ids_returns_well_formed_ids_in_order(self):
        events, policies = extract_citation_ids(
            "POL-002 and evt-006, then EVT-002, EVT-006 again, POL-001, xEVT-009 and EVT-1_x."
        )
        self.assertEqual(events, ["EVT-006", "EVT-002"])
        self.assertEqual(policies, ["POL-002", "POL-001"])

    def test_extract_citation_ids_handles_uncited_report(self):
        self.assertEqual(extract_citation_ids("No identifiers here."), ([], []))

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


class TestProviderBoundary(unittest.TestCase):
    """Drive the real OpenAI SDK against an in-process HTTP transport; no network is used."""

    def setUp(self):
        self.requests = []
        self.client_kwargs = {}
        self.handler = None
        self.incident = {"id": "INC-1", "events": [{"id": "EVT-1"}]}
        self.analysis = {"risk_score": 40, "evidence_ids": ["EVT-1"]}
        self.policies = [{"id": "POL-1", "title": "t", "text": "x"}]

    def fake_openai(self, **kwargs):
        self.client_kwargs = kwargs

        def record(request):
            self.requests.append(request)
            return self.handler(request)

        # max_retries=0 is a test-only override so SDK retry backoff does not slow the suite.
        return OpenAI(
            **dict(kwargs, max_retries=0),
            http_client=httpx.Client(transport=httpx.MockTransport(record)),
        )

    def generate(self, handler, model="test-model"):
        self.handler = handler
        with patch.object(ai_client, "OpenAI", side_effect=self.fake_openai):
            return generate_report(FAKE_KEY, self.incident, self.analysis, self.policies, model=model)

    def assert_safe_failure(self, handler):
        self.requests.clear()
        with self.assertRaises(AIReportError) as caught:
            self.generate(handler)
        self.assertEqual(len(self.requests), 1)
        self.assertNotIn(FAKE_KEY, str(caught.exception))
        return caught.exception

    def test_valid_response_returns_stripped_report(self):
        report = self.generate(lambda request: httpx.Response(200, json=chat_completion("  EVT-1 per POL-1.\n")))
        self.assertEqual(report, "EVT-1 per POL-1.")

    def test_request_uses_documented_endpoint_timeout_and_payload(self):
        self.generate(lambda request: httpx.Response(200, json=chat_completion("EVT-1 POL-1")), model="chosen/model")
        self.assertEqual(self.client_kwargs["base_url"], ai_client.BASE_URL)
        self.assertEqual(self.client_kwargs["timeout"], 60.0)
        self.assertEqual(self.client_kwargs["max_retries"], 1)  # a failure surfaces in about two minutes, not three
        self.assertEqual(len(self.requests), 1)
        request = self.requests[0]
        self.assertEqual(str(request.url), ai_client.BASE_URL + "chat/completions")
        body = json.loads(request.content)
        self.assertEqual(body["model"], "chosen/model")
        self.assertEqual(body["temperature"], 0.2)
        self.assertEqual(body["max_tokens"], 2000)
        self.assertEqual([message["role"] for message in body["messages"]], ["system", "user"])
        system = body["messages"][0]["content"]
        for section in ("Observed facts", "Inferred risk", "Unknowns and limitations"):
            self.assertIn(section, system)
        self.assertIn("not proof of compromise", system)
        sent = json.loads(body["messages"][1]["content"])
        self.assertEqual(sent["incident"], self.incident)
        self.assertEqual(sent["deterministic_rule_analysis"], self.analysis)
        self.assertEqual(sent["retrieved_company_policies"], self.policies)
        self.assertNotIn(FAKE_KEY, request.content.decode("utf-8"))

    def test_model_defaults_to_environment_override(self):
        with patch.dict(os.environ, {"NEBIUS_MODEL": "env/model"}):
            self.generate(lambda request: httpx.Response(200, json=chat_completion("EVT-1 POL-1")), model=None)
        self.assertEqual(json.loads(self.requests[0].content)["model"], "env/model")

    def test_timeout_is_a_safe_error(self):
        def timeout(request):
            raise httpx.ReadTimeout("timed out", request=request)

        self.assert_safe_failure(timeout)

    def test_connection_failure_is_a_safe_error(self):
        def refused(request):
            raise httpx.ConnectError("refused", request=request)

        self.assert_safe_failure(refused)

    def test_http_errors_are_safe_and_do_not_leak_key(self):
        for status in (401, 403, 404, 429, 500, 503):
            with self.subTest(status=status):
                # A provider that echoes the credential must still not surface it to the UI.
                self.assert_safe_failure(
                    lambda request, status=status: httpx.Response(
                        status, json={"error": {"message": f"rejected key {FAKE_KEY}"}}
                    )
                )

    def test_http_errors_name_the_cause(self):
        expected = {401: "rejected the API key", 403: "not allowed to use this model",
                    404: "Model test-model was not found", 429: "quota", 500: "HTTP 500"}
        for status, phrase in expected.items():
            with self.subTest(status=status):
                error = self.assert_safe_failure(
                    lambda request, status=status: httpx.Response(status, json={"error": {"message": "x"}})
                )
                self.assertIn(phrase, str(error))

    def test_timeout_and_connection_errors_name_the_cause(self):
        def timeout(request):
            raise httpx.ReadTimeout("timed out", request=request)

        def refused(request):
            raise httpx.ConnectError("refused", request=request)

        self.assertIn("60 seconds", str(self.assert_safe_failure(timeout)))
        self.assertIn("Could not reach", str(self.assert_safe_failure(refused)))

    def test_exhausted_token_budget_is_explained(self):
        error = self.assert_safe_failure(
            lambda request: httpx.Response(200, json=chat_completion(None, finish_reason="length"))
        )
        self.assertIn("token budget", str(error))

    def test_reasoning_block_is_removed_from_report(self):
        content = "<think>private reasoning EVT-9</think>\n## Observed facts\nEVT-1 per POL-1."
        report = self.generate(lambda request: httpx.Response(200, json=chat_completion(content)))
        self.assertEqual(report, "## Observed facts\nEVT-1 per POL-1.")
        only_thinking = chat_completion("<think>still thinking", finish_reason="length")
        self.assertIn("token budget", str(self.assert_safe_failure(lambda request: httpx.Response(200, json=only_thinking))))

    def test_invalid_json_is_a_safe_error(self):
        self.assert_safe_failure(
            lambda request: httpx.Response(
                200, content=b"<html>gateway</html>", headers={"content-type": "application/json"}
            )
        )

    def test_non_json_content_type_is_a_safe_error(self):
        self.assert_safe_failure(
            lambda request: httpx.Response(200, content=b"<html>gateway</html>", headers={"content-type": "text/html"})
        )

    def test_unexpected_response_structures_are_safe_errors(self):
        bodies = {
            "list": ["unexpected"],
            "no choices": {key: value for key, value in chat_completion("x").items() if key != "choices"},
            "empty choices": dict(chat_completion("x"), choices=[]),
        }
        for label, body in bodies.items():
            with self.subTest(body=label):
                self.assert_safe_failure(lambda request, body=body: httpx.Response(200, json=body))

    def test_missing_or_blank_content_is_a_safe_error(self):
        for content in (None, "", "   \n"):
            with self.subTest(content=content):
                self.assert_safe_failure(
                    lambda request, content=content: httpx.Response(200, json=chat_completion(content))
                )


if __name__ == "__main__":
    unittest.main()
