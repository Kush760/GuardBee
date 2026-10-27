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


def start_app():
    return AppTest.from_file(str(APP_PATH), default_timeout=30).run()


def open_incident(incident_id):
    """Reach an incident the way an analyst does: Dashboard -> Recent Incidents -> View."""
    app = start_app()
    app.button(key=f"dash_view_{incident_id}").click().run()
    return app


def page_text(app):
    return "\n".join(
        [element.value for element in app.markdown]
        + [element.value for element in app.caption]
        + [element.value for element in app.subheader]
        + [str(element.value) for element in app.success]
        + [str(element.value) for element in app.error]
        + [str(element.value) for element in app.warning]
        + [str(element.value) for element in app.info]
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

    def approve_validated_report(self, incident_id="INC-1001"):
        self.use_report(VALID_REPORT)
        app = open_incident(incident_id)
        app.button(key="ai_request_btn").click().run()
        app.button(key="btn_approve").click().run()
        return app

    # -- Rendering and navigation -------------------------------------------------
    def test_dashboard_and_every_incident_render(self):
        dashboard = start_app()
        self.assertFalse(dashboard.exception)
        self.assertEqual(len(dashboard.get("image")), 1)  # the GuardBee logo replaces the text title
        self.assertIn("AI-Powered Security Analysis", page_text(dashboard))
        self.assertIn("Demo Only", page_text(dashboard))
        for incident_id in ("INC-1001", "INC-1002", "INC-1003"):
            with self.subTest(incident=incident_id):
                app = open_incident(incident_id)
                self.assertFalse(app.exception)
                self.assertEqual(app.title[0].value, "Security Incidents")
                self.assertEqual(app.radio(key="incident_picker").value, incident_id)

    def test_app_injects_no_dynamic_html(self):
        source = APP_PATH.read_text(encoding="utf-8")
        self.assertNotIn("unsafe_allow_html", source)
        self.assertEqual(re.findall(r"st\.html\((.*?)\)", source), ["STYLES"])

    def test_dashboard_counts_come_from_engine(self):
        values = metric_values(start_app())
        self.assertEqual(values["Total valid incidents"], "3")
        self.assertEqual(values["Suspicious"], "—")
        self.assertEqual(values["Normal"], "—")
        self.assertEqual(values["Insufficient evidence"], "—")
        self.assertEqual(values["Rejected records"], "0")
        self.assertIn("By severity", page_text(start_app()))  # no classification is inferred

    def test_view_all_opens_security_incidents(self):
        app = start_app()
        app.button(key="dash_view_all").click().run()
        self.assertEqual(app.title[0].value, "Security Incidents")

    def test_search_filters_incident_list(self):
        app = open_incident("INC-1001")
        app.text_input(key="incident_search").input("unfamiliar login").run()
        self.assertEqual(app.radio(key="incident_picker").options, ["INC-1002 (40/100) — Unfamiliar login requires review"])
        self.assertEqual(app.radio(key="incident_picker").value, "INC-1002")
        app.selectbox(key="incident_filter").set_value("High severity").run()
        self.assertIn("No incidents match", page_text(app))

    # -- Classification, severity, priority ----------------------------------------
    def test_unclassified_engine_output_is_never_labelled(self):
        app = open_incident("INC-1003")
        text = page_text(app)
        self.assertIn("NOT CLASSIFIED", text)
        self.assertNotIn("green-background[NORMAL]", text)
        self.assertIn("not a probability", text)
        self.assertEqual(metric_values(app)["Classification"], "—")

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
            values = metric_values(start_app())
            self.assertEqual(values["Suspicious"], "1")
            self.assertEqual(values["Normal"], "1")
            self.assertEqual(values["Insufficient Evidence"], "1")

            normal = open_incident("INC-1003")
            self.assertIn(":green-background[NORMAL]", page_text(normal))
            self.assertIn("No suspicious pattern was detected by the configured rules", page_text(normal))
            self.assertEqual(metric_values(normal)["Severity"], "Not assigned")

            unclear = open_incident("INC-1002")
            self.assertIn("not sufficient to classify this activity", page_text(unclear))
            self.assertNotIn("SUSPICIOUS", page_text(unclear))
            self.assertEqual(metric_values(unclear)["Investigation priority"], "Routine review")

    # -- Evidence -------------------------------------------------------------------
    def test_timeline_is_chronological_and_rules_match_engine(self):
        app = open_incident("INC-1001")
        timeline = app.dataframe[0].value
        self.assertEqual(list(timeline["Time (UTC)"]), sorted(timeline["Time (UTC)"]))
        rules = app.dataframe[1].value
        expected = engine.analyze_incident(data_loader.load_incidents(APP_PATH.parent / "data" / "incidents.json")[0])
        self.assertEqual(list(rules["Rule"]), [hit["rule_id"] for hit in expected["rule_hits"]])
        self.assertEqual(list(rules["Points"]), [hit["points"] for hit in expected["rule_hits"]])
        self.assertIn("`GB-RULE-002` → `EVT-006`", page_text(app))

    def test_data_text_is_shown_literally(self):
        hostile = "**bold** [x](https://evil.example) <img src=x onerror=alert(1)> admin@evil.example"
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
            app = open_incident("INC-X")
        self.assertFalse(app.exception)
        text = page_text(app)
        self.assertIn("`" + hostile + "`", text)  # identifiers render as literal inline code
        outside_code = re.sub(r"`[^`]*`", "", text)  # code spans never render Markdown or HTML
        self.assertNotIn("[x](https", outside_code)
        self.assertIsNone(re.search(r"(?<!\\)<img", outside_code))
        self.assertIn("\\<img", outside_code)

    def test_load_error_shows_no_counts(self):
        with patch.object(data_loader, "load_incidents", side_effect=data_loader.DataValidationError("broken")):
            app = start_app()
        self.assertIn("could not load its synthetic data safely", page_text(app))
        self.assertEqual(len(app.metric), 0)

    # -- AI report and decisions --------------------------------------------------------
    def test_validated_report_allows_exactly_one_decision(self):
        self.use_report(VALID_REPORT)
        app = open_incident("INC-1001")
        self.assertTrue(app.button(key="btn_approve").disabled)

        app.button(key="ai_request_btn").click().run()
        text = page_text(app)
        for identifier in ("`EVT-006`", "`EVT-002`", "`POL-001`"):
            self.assertIn(identifier, text)
        self.assertFalse(app.button(key="btn_approve").disabled)

        app.button(key="btn_approve").click().run()
        self.assertEqual(len(app.session_state["audit"]), 1)
        self.assertTrue(app.button(key="btn_approve").disabled)
        self.assertTrue(app.button(key="btn_reject").disabled)
        self.assertIn("APPROVED recorded at", page_text(app))

        app.run()  # a rerender must not add a duplicate audit row
        self.assertEqual(len(app.session_state["audit"]), 1)

    def test_audit_history_shows_decision_and_links_back(self):
        app = self.approve_validated_report()
        app.button(key="open_audit").click().run()
        self.assertEqual(app.title[0].value, "Audit History")
        history = app.dataframe[0].value
        self.assertEqual(list(history["Incident"]), ["INC-1001"])
        self.assertEqual(list(history["Decision"]), ["✅ APPROVED"])
        self.assertIn("SIMULATION ONLY", page_text(app))

        app.button(key="audit_open").click().run()
        self.assertEqual(app.title[0].value, "Security Incidents")
        self.assertEqual(app.radio(key="incident_picker").value, "INC-1001")
        self.assertTrue(app.button(key="btn_approve").disabled)  # the recorded decision still locks it

    def test_changing_incident_invalidates_report(self):
        self.use_report(VALID_REPORT)
        app = open_incident("INC-1001")
        app.button(key="ai_request_btn").click().run()
        self.assertIsNotNone(app.session_state["report"])
        app.radio(key="incident_picker").set_value("INC-1002").run()
        self.assertIsNone(app.session_state["report"])
        self.assertTrue(app.button(key="btn_approve").disabled)

    def test_invalid_citations_keep_decision_locked(self):
        self.use_report("EVT-999 per POL-001.")
        app = open_incident("INC-1001")
        app.button(key="ai_request_btn").click().run()
        self.assertIsNone(app.session_state["report"])
        self.assertIn("EVT\\-999", page_text(app))
        self.assertTrue(app.button(key="btn_approve").disabled)

    def test_provider_failure_offers_retry_without_fabricating(self):
        self.generate.side_effect = ai_client.AIReportError("Nebius Token Factory did not return a report.")
        app = open_incident("INC-1001")
        app.button(key="ai_request_btn").click().run()
        self.assertIsNone(app.session_state["report"])
        self.assertIn("did not return a report", page_text(app))
        self.assertTrue(app.button(key="btn_approve").disabled)

        self.use_report(VALID_REPORT)
        app.button(key="ai_retry_btn").click().run()
        self.assertEqual(self.generate.call_count, 2)
        self.assertEqual(app.session_state["report"], VALID_REPORT)
        self.assertFalse(app.button(key="btn_approve").disabled)


if __name__ == "__main__":
    unittest.main()
