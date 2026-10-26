"""Headless Streamlit UI tests. The AI provider is always mocked; no network call is made."""

import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

import ai_client
import data_loader
import engine

APP = str(Path(__file__).resolve().parents[1] / "app.py")
VALID_REPORT = "## Observed facts\nEVT-006 succeeded after failures EVT-002, per POL-001."


def open_app(view="dashboard", incident_id=None):
    app = AppTest.from_file(APP, default_timeout=30)
    app.session_state["view"] = view
    if incident_id:
        app.session_state["selected_incident_id"] = incident_id
    return app.run()


def page_html(app):
    return "\n".join(element.value for element in app.markdown)


class TestGuardBeeUI(unittest.TestCase):
    def setUp(self):
        # Any test that reaches the provider without its own mock fails instead of calling Nebius.
        patcher = patch.object(
            ai_client, "generate_report", side_effect=AssertionError("live provider call attempted")
        )
        self.generate = patcher.start()
        self.addCleanup(patcher.stop)

    def test_every_view_renders(self):
        for view, incident_id in [
            ("dashboard", None),
            ("incidents", None),
            ("audit", None),
            ("detail", "INC-1001"),
            ("detail", "INC-1002"),
            ("detail", "INC-1003"),
        ]:
            with self.subTest(view=view, incident=incident_id):
                app = open_app(view, incident_id)
                self.assertFalse(app.exception)

    def test_open_buttons_reach_detail_and_sidebar_navigation_still_works(self):
        app = open_app()
        app.button(key="dash_open_INC-1001").click().run()
        self.assertEqual(app.session_state["view"], "detail")
        self.assertEqual(app.session_state["selected_incident_id"], "INC-1001")
        app.button(key="ai_request_btn")  # detail controls are rendered

        app.run()  # an unrelated rerun must not bounce the analyst out of the detail view
        self.assertEqual(app.session_state["view"], "detail")

        app.sidebar.radio(key="nav_radio").set_value("📋  Audit History").run()
        self.assertEqual(app.session_state["view"], "audit")

        app.sidebar.radio(key="nav_radio").set_value("🛡️  Security Incidents").run()
        app.button(key="inc_open_INC-1002").click().run()
        self.assertEqual(app.session_state["view"], "detail")
        self.assertEqual(app.session_state["selected_incident_id"], "INC-1002")

    def test_low_severity_is_not_labelled_normal(self):
        for view, incident_id in [("incidents", None), ("detail", "INC-1003"), ("dashboard", None)]:
            with self.subTest(view=view):
                html = page_html(open_app(view, incident_id))
                self.assertNotIn("NORMAL ACTIVITY", html)
                self.assertNotIn("● SUSPICIOUS", html)
                self.assertIn("not proof of compromise", html)

    def test_engine_classification_and_priority_are_displayed_when_provided(self):
        original = engine.analyze_incident

        def classified(incident):
            return dict(original(incident), classification="insufficient_evidence", priority="Routine review")

        with patch.object(engine, "analyze_incident", side_effect=classified):
            html = page_html(open_app("detail", "INC-1002"))
        self.assertIn("INSUFFICIENT EVIDENCE", html)
        self.assertIn("Investigation Priority", html)
        self.assertIn("Routine review", html)

    def test_dynamic_content_is_escaped(self):
        hostile = "<img src=x onerror=alert(1)>"
        incident = {
            "id": "INC-X",
            "title": hostile,
            "account": hostile,
            "department": hostile,
            "known_ips": ["203.0.113.1"],
            "events": [
                {"id": "EVT-X1", "time_utc": "2026-01-01T00:00:00Z", "type": "login_success",
                 "ip": "198.51.100.9", "country": hostile},
            ],
        }
        with patch.object(data_loader, "load_incidents", return_value=[incident]):
            for view, incident_id in [("dashboard", None), ("incidents", None), ("detail", "INC-X")]:
                with self.subTest(view=view):
                    html = page_html(open_app(view, incident_id))
                    self.assertNotIn(hostile, html)
                    self.assertIn("&lt;img src=x onerror=alert(1)&gt;", html)

    def test_validated_report_shows_citations_and_allows_one_decision(self):
        self.generate.side_effect = None
        self.generate.return_value = VALID_REPORT
        app = open_app("detail", "INC-1001")
        self.assertTrue(app.button(key="btn_approve").disabled)

        app.button(key="ai_request_btn").click().run()
        html = page_html(app)
        self.assertIn("Evidence cited by the AI", html)
        for identifier in ("EVT-006", "EVT-002", "POL-001"):
            self.assertIn(identifier, html)
        self.assertFalse(app.button(key="btn_approve").disabled)

        app.button(key="btn_approve").click().run()
        self.assertEqual(len(app.session_state["audit"]), 1)
        self.assertTrue(app.button(key="btn_approve").disabled)
        self.assertTrue(app.button(key="btn_reject").disabled)

        app.session_state["view"] = "audit"
        app.run()
        audit_html = page_html(app)
        self.assertIn("INC-1001", audit_html)
        self.assertIn("APPROVED", audit_html)

    def test_invalid_citations_keep_decision_locked(self):
        self.generate.side_effect = None
        self.generate.return_value = "EVT-999 per POL-001."
        app = open_app("detail", "INC-1001")
        app.button(key="ai_request_btn").click().run()
        self.assertIsNone(app.session_state["report"])
        self.assertIn("EVT-999", page_html(app))
        self.assertTrue(app.button(key="btn_approve").disabled)

    def test_provider_failure_offers_retry_without_fabricating(self):
        self.generate.side_effect = ai_client.AIReportError("Nebius Token Factory did not return a report.")
        app = open_app("detail", "INC-1001")
        app.button(key="ai_request_btn").click().run()
        self.assertIsNone(app.session_state["report"])
        self.assertIn("did not return a report", page_html(app))
        self.assertTrue(app.button(key="btn_approve").disabled)

        self.generate.side_effect = None
        self.generate.return_value = VALID_REPORT
        app.button(key="ai_retry_btn").click().run()
        self.assertEqual(self.generate.call_count, 2)
        self.assertEqual(app.session_state["report"], VALID_REPORT)
        self.assertFalse(app.button(key="btn_approve").disabled)


if __name__ == "__main__":
    unittest.main()
