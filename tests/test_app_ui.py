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
    """Reach an incident the way an analyst does: Dashboard -> View All -> pick it from the list."""
    app = start_app()
    app.button(key="dash_view_all").click().run()
    app.radio(key="incident_picker").set_value(incident_id).run()
    return app


def unclassified(incident):
    """Engine output as it looked before classification and priority were provided."""
    analysis = dict(ORIGINAL_ANALYZE(incident))
    analysis.pop("classification", None)
    analysis.pop("investigation_priority", None)
    return analysis


ORIGINAL_ANALYZE = engine.analyze_incident


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
        self.assertEqual(dashboard.title[0].value, "Welcome to GuardBee")
        self.assertIn("Demo only", page_text(dashboard))  # sidebar disclaimer, shown on every page
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
        app = start_app()
        values = metric_values(app)
        self.assertEqual(values["Total valid incidents"], "13")
        self.assertEqual(values["Suspicious"], "6")
        self.assertEqual(values["Normal"], "3")
        self.assertEqual(values["Insufficient Evidence"], "4")
        self.assertEqual(values["Rejected records"], "0")
        self.assertIn("By classification", page_text(app))

    def test_dashboard_falls_back_to_severity_without_engine_classes(self):
        with patch.object(engine, "analyze_incident", side_effect=unclassified):
            app = start_app()
        values = metric_values(app)
        self.assertEqual(values["Suspicious"], "—")
        self.assertEqual(values["Insufficient evidence"], "—")
        self.assertIn("By severity", page_text(app))  # no classification is inferred

    def test_view_all_opens_security_incidents(self):
        app = start_app()
        app.button(key="dash_view_all").click().run()
        self.assertEqual(app.title[0].value, "Security Incidents")

    def test_recent_incident_view_opens_that_incident(self):
        app = start_app()
        app.button(key="dash_view_INC-1014").click().run()  # INC-1014 has the latest event
        self.assertEqual(app.title[0].value, "Security Incidents")
        self.assertEqual(app.radio(key="incident_picker").value, "INC-1014")

    def test_search_filters_incident_list(self):
        app = open_incident("INC-1001")
        app.text_input(key="incident_search").input("requires review").run()
        options = app.radio(key="incident_picker").options
        self.assertEqual(len(options), 1)
        self.assertIn("**INC-1002**", options[0])
        self.assertEqual(app.radio(key="incident_picker").value, "INC-1002")
        app.selectbox(key="incident_filter").set_value("High severity").run()
        self.assertIn("No incidents match", page_text(app))

    def test_full_report_dialog_shows_engine_rules(self):
        app = open_incident("INC-1001")
        app.button(key="engine_full_report").click().run()
        self.assertFalse(app.exception)
        rules = [frame.value for frame in app.dataframe if "Rule" in frame.value.columns]
        self.assertTrue(any(list(frame["Rule"])[:1] == ["GB-RULE-001"] for frame in rules))
        self.assertGreaterEqual(len(rules), 2)  # the Rules tab table plus the dialog's own copy

    # -- Classification, severity, priority ----------------------------------------
    def test_unclassified_engine_output_is_never_labelled(self):
        with patch.object(engine, "analyze_incident", side_effect=unclassified):
            app = open_incident("INC-1003")
        text = page_text(app)
        self.assertIn("NOT CLASSIFIED", text)
        self.assertNotIn("green-background[NORMAL]", text)
        self.assertIn("not a probability", text)
        self.assertEqual(metric_values(app)["Priority"], "—")

    def test_engine_classification_priority_and_unassigned_severity_render(self):
        suspicious = open_incident("INC-1001")
        self.assertIn(":red-background[SUSPICIOUS]", page_text(suspicious))
        self.assertEqual(metric_values(suspicious)["Severity"], "HIGH")
        self.assertEqual(metric_values(suspicious)["Priority"], "HIGH")

        normal = open_incident("INC-1003")
        self.assertIn(":green-background[NORMAL]", page_text(normal))
        self.assertIn("No suspicious pattern was detected by the configured rules", page_text(normal))
        self.assertEqual(metric_values(normal)["Severity"], "Not assigned")
        self.assertEqual(metric_values(normal)["Priority"], "NONE")

        unclear = open_incident("INC-1002")
        self.assertIn("not sufficient to classify this activity", page_text(unclear))
        self.assertNotIn("SUSPICIOUS", page_text(unclear))
        self.assertEqual(metric_values(unclear)["Priority"], "LOW")

    # -- Evidence -------------------------------------------------------------------
    def test_timeline_is_chronological_and_rules_match_engine(self):
        app = open_incident("INC-1001")
        timeline = app.dataframe[0].value
        self.assertEqual(list(timeline["Time (UTC)"]), sorted(timeline["Time (UTC)"]))
        self.assertEqual(list(timeline["Rule evidence"]), ["—"] + ["✓ Evidence"] * 5)  # text, never a checkbox
        rules = app.dataframe[1].value
        expected = engine.analyze_incident(data_loader.load_incidents(APP_PATH.parent / "data" / "incidents.json")[0])
        self.assertEqual(list(rules["Rule"]), [hit["rule_id"] for hit in expected["rule_hits"]])
        self.assertEqual(list(rules["Points"]), [hit["points"] for hit in expected["rule_hits"]])
        self.assertIn("`GB-RULE-003` → `EVT-002` `EVT-003` `EVT-004` `EVT-005` `EVT-006`", page_text(app))

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
        self.assertEqual(list(history["Simulation only"]), ["Yes"])
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

    def test_approve_outcome_describes_the_engine_action(self):
        self.use_report("EVT-202 per POL-001.")
        app = open_incident("INC-1003")  # NORMAL: the engine proposes no containment
        app.button(key="ai_request_btn").click().run()
        app.button(key="btn_approve").click().run()
        outcome = app.session_state["audit"][-1]["outcome"]
        self.assertIn("No containment recommendation", outcome)
        self.assertNotIn("session-revocation", outcome)

    def test_recorded_decision_is_shown_after_switching_incidents(self):
        app = self.approve_validated_report()
        app.radio(key="incident_picker").set_value("INC-1002").run()
        self.assertNotIn("Last recorded decision", page_text(app))
        app.radio(key="incident_picker").set_value("INC-1001").run()
        self.assertIn("Last recorded decision\\: APPROVED", page_text(app))
        app.button(key="open_audit").click().run()
        self.assertEqual(app.title[0].value, "Audit History")

    def test_ai_report_links_and_images_are_not_rendered(self):
        self.use_report(
            "## Facts\nEVT-006 per POL-001. [click](https://evil.example/x) ![p](https://evil.example/p.png) "
            "owner@evil.example https://evil.example www.evil.example <b>x</b>"
        )
        app = open_incident("INC-1001")
        app.button(key="ai_request_btn").click().run()
        shown = next(element.value for element in app.markdown if "EVT-006 per POL-001" in element.value)
        self.assertIn("## Facts", shown)  # headings and lists still render
        self.assertNotIn("](", shown)  # Markdown links and images are reduced to their text
        outside_code = re.sub(r"`[^`]*`", "", shown)
        for address in ("evil.example", "://", "@"):
            self.assertNotIn(address, outside_code)  # addresses only appear as literal code
        self.assertIn("`owner@evil.example`", shown)
        self.assertIn("`https://evil.example`", shown)
        self.assertIn("\\<b>", shown)

    def test_filter_options_show_match_counts(self):
        options = open_incident("INC-1001").selectbox(key="incident_filter").options
        self.assertIn("All (13)", options)
        self.assertIn("Low severity (0)", options)
        self.assertIn("Suspicious (6)", options)

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
        self.assertTrue(any("AI report failed" in element.value for element in app.error))  # shown beside the button
        self.assertTrue(app.button(key="btn_approve").disabled)

        self.use_report(VALID_REPORT)
        app.button(key="ai_retry_btn").click().run()
        self.assertEqual(self.generate.call_count, 2)
        self.assertEqual(app.session_state["report"], VALID_REPORT)
        self.assertFalse(app.button(key="btn_approve").disabled)


if __name__ == "__main__":
    unittest.main()
