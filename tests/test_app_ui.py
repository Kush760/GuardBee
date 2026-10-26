"""Headless Streamlit UI tests. The AI provider is always mocked; no network call is made."""

import re
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

import ai_client
import data_loader
import engine

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"
VALID_REPORT = "## Observed facts\nEVT-006 succeeded after failures EVT-002, per POL-001."


def open_app(page="Dashboard", incident_id=None):
    app = AppTest.from_file(str(APP_PATH), default_timeout=30)
    app.session_state["page"] = page
    if incident_id:
        app.session_state["current_incident_id"] = incident_id
    return app.run()


def markdown_text(app):
    return "\n".join(
        [element.value for element in app.markdown]
        + [element.value for element in app.caption]
        + [element.value for element in app.subheader]
        + [str(element.value) for element in app.success]
        + [str(element.value) for element in app.error]
        + [str(element.value) for element in app.warning]
    )


def metric_values(app):
    return {metric.label: metric.value for metric in app.metric}


class TestGuardBeeUI(unittest.TestCase):
    def setUp(self):
        # Any path that reaches the provider without its own mock fails instead of calling Nebius.
        patcher = patch.object(
            ai_client, "generate_report", side_effect=AssertionError("live provider call attempted")
        )
        self.generate = patcher.start()
        self.addCleanup(patcher.stop)

    def use_report(self, report):
        self.generate.side_effect = None
        self.generate.return_value = report

    def test_every_page_and_incident_renders(self):
        for page, incident_id in [
            ("Dashboard", None),
            ("Audit History", None),
            ("Security Incidents", "INC-1001"),
            ("Security Incidents", "INC-1002"),
            ("Security Incidents", "INC-1003"),
        ]:
            with self.subTest(page=page, incident=incident_id):
                self.assertFalse(open_app(page, incident_id).exception)

    def test_app_renders_no_raw_html(self):
        self.assertNotIn("unsafe_allow_html", APP_PATH.read_text(encoding="utf-8"))

    def test_dashboard_open_button_shows_selected_incident(self):
        app = open_app()
        app.selectbox(key="dashboard_pick").set_value("INC-1002").run()
        app.button(key="dashboard_open").click().run()
        self.assertEqual(app.sidebar.radio(key="page").value, "Security Incidents")
        self.assertEqual(app.selectbox(key="incident_picker").value, "INC-1002")
        self.assertIn("INC\\-1002", markdown_text(app))

    def test_selection_survives_page_changes(self):
        app = open_app("Security Incidents")
        app.selectbox(key="incident_picker").set_value("INC-1003").run()
        app.sidebar.radio(key="page").set_value("Audit History").run()
        app.sidebar.radio(key="page").set_value("Security Incidents").run()
        self.assertEqual(app.selectbox(key="incident_picker").value, "INC-1003")

    def test_unclassified_engine_output_is_never_labelled(self):
        dashboard = open_app()
        values = metric_values(dashboard)
        self.assertEqual(values["Suspicious"], "—")
        self.assertEqual(values["Normal"], "—")
        detail = open_app("Security Incidents", "INC-1003")
        text = markdown_text(detail)
        self.assertIn("NOT CLASSIFIED", text)
        self.assertNotIn("NORMAL]", text)
        self.assertIn("not proof of compromise", text)

    def test_engine_classification_priority_and_unassigned_severity_render(self):
        original = engine.analyze_incident
        overrides = {
            "INC-1001": {"classification": "SUSPICIOUS", "investigation_priority": "Urgent review"},
            "INC-1002": {"classification": "INSUFFICIENT_EVIDENCE", "investigation_priority": "Routine review"},
            "INC-1003": {"classification": "NORMAL", "severity": None, "investigation_priority": "None"},
        }

        def classified(incident):
            return dict(original(incident), **overrides[incident["id"]])

        with patch.object(engine, "analyze_incident", side_effect=classified):
            values = metric_values(open_app())
            self.assertEqual(values["Suspicious"], "1")
            self.assertEqual(values["Insufficient Evidence"], "1")
            self.assertEqual(values["Normal"], "1")
            self.assertEqual(values["Severity not assigned"], "1")

            normal = open_app("Security Incidents", "INC-1003")
            self.assertIn(":green-background[NORMAL]", markdown_text(normal))
            self.assertIn("No suspicious pattern was detected by the configured rules", markdown_text(normal))
            self.assertEqual(metric_values(normal)["Severity"], "Not assigned")

            unclear = open_app("Security Incidents", "INC-1002")
            self.assertIn("not sufficient to classify this activity", markdown_text(unclear))
            self.assertEqual(metric_values(unclear)["Investigation priority"], "Routine review")

    def test_data_text_is_shown_literally(self):
        hostile = "**bold** [x](https://evil.example) <img src=x onerror=alert(1)>"
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
            app = open_app("Security Incidents", "INC-X")
        self.assertFalse(app.exception)
        text = markdown_text(app)
        self.assertNotIn("[x](https", text)
        self.assertIsNone(re.search(r"(?<!\\)<img", text))
        self.assertIn("\\<img", text)

    def test_timeline_is_chronological(self):
        app = open_app("Security Incidents", "INC-1001")
        times = list(app.dataframe[1].value["Time (UTC)"])
        self.assertEqual(times, sorted(times))

    def test_validated_report_allows_exactly_one_decision(self):
        self.use_report(VALID_REPORT)
        app = open_app("Security Incidents", "INC-1001")
        self.assertTrue(app.button(key="btn_approve").disabled)

        app.button(key="ai_request_btn").click().run()
        text = markdown_text(app)
        for identifier in ("`EVT-006`", "`EVT-002`", "`POL-001`"):
            self.assertIn(identifier, text)
        self.assertFalse(app.button(key="btn_approve").disabled)

        app.button(key="btn_approve").click().run()
        self.assertEqual(len(app.session_state["audit"]), 1)
        self.assertTrue(app.button(key="btn_approve").disabled)
        self.assertTrue(app.button(key="btn_reject").disabled)
        self.assertIn("APPROVED recorded at", markdown_text(app))

        app.run()  # a rerender must not add a duplicate audit row
        self.assertEqual(len(app.session_state["audit"]), 1)

        app.sidebar.radio(key="page").set_value("Audit History").run()
        history = app.dataframe[0].value
        self.assertEqual(list(history["Incident"]), ["INC-1001"])
        self.assertEqual(list(history["Decision"]), ["APPROVED"])

    def test_changing_incident_invalidates_report(self):
        self.use_report(VALID_REPORT)
        app = open_app("Security Incidents", "INC-1001")
        app.button(key="ai_request_btn").click().run()
        self.assertIsNotNone(app.session_state["report"])
        app.selectbox(key="incident_picker").set_value("INC-1002").run()
        self.assertIsNone(app.session_state["report"])
        self.assertTrue(app.button(key="btn_approve").disabled)

    def test_invalid_citations_keep_decision_locked(self):
        self.use_report("EVT-999 per POL-001.")
        app = open_app("Security Incidents", "INC-1001")
        app.button(key="ai_request_btn").click().run()
        self.assertIsNone(app.session_state["report"])
        self.assertIn("EVT\\-999", markdown_text(app))
        self.assertTrue(app.button(key="btn_approve").disabled)

    def test_provider_failure_offers_retry_without_fabricating(self):
        self.generate.side_effect = ai_client.AIReportError("Nebius Token Factory did not return a report.")
        app = open_app("Security Incidents", "INC-1001")
        app.button(key="ai_request_btn").click().run()
        self.assertIsNone(app.session_state["report"])
        self.assertIn("did not return a report", markdown_text(app))
        self.assertTrue(app.button(key="btn_approve").disabled)

        self.use_report(VALID_REPORT)
        app.button(key="ai_retry_btn").click().run()
        self.assertEqual(self.generate.call_count, 2)
        self.assertEqual(app.session_state["report"], VALID_REPORT)
        self.assertFalse(app.button(key="btn_approve").disabled)


if __name__ == "__main__":
    unittest.main()
