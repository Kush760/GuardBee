"""Tests for stdlib SQLite audit persistence (MVP Scope v2.2 §6)."""

from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from audit_store import (
    AuditStoreError,
    get_decision_by_report_id,
    initialize_database,
    list_decisions,
    save_decision,
)
from workflow import analysis_context_id, build_decision_record


def _sample_record(report_id: str = "report-1", **overrides):
    base = {
        "time_utc": "2026-01-01T00:00:00+00:00",
        "incident_id": "INC-1",
        "actor": "demo-analyst",
        "decision": "APPROVED",
        "outcome": "simulated",
        "simulation_only": True,
        "report_id": report_id,
        "report_context_id": "ctx-1",
        "evidence_ids": ["EVT-1"],
        "policy_ids": ["POL-1"],
        "status": "RECORDED",
    }
    base.update(overrides)
    return base


class TestAuditStore(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmpdir.name) / "audit.db"

    def tearDown(self):
        # Windows can briefly keep the SQLite file locked after the last close.
        try:
            self._tmpdir.cleanup()
        except PermissionError:
            pass

    def test_initialize_database_creates_schema_before_any_record_is_saved(self):
        initialize_database(path=self.db_path)
        self.assertTrue(self.db_path.is_file())
        connection = sqlite3.connect(self.db_path)
        try:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table';"
                )
            }
        finally:
            connection.close()
        self.assertIn("audit_decisions", tables)

    def test_save_and_reload_survives_new_connection(self):
        saved = save_decision(_sample_record(), path=self.db_path)
        self.assertEqual(saved["decision"], "APPROVED")
        self.assertEqual(saved["evidence_ids"], ["EVT-1"])
        self.assertEqual(saved["policy_ids"], ["POL-1"])
        self.assertTrue(saved["simulation_only"])

        reloaded = get_decision_by_report_id("report-1", path=self.db_path)
        self.assertIsNotNone(reloaded)
        self.assertEqual(reloaded["incident_id"], "INC-1")
        self.assertEqual(reloaded["status"], "RECORDED")
        self.assertEqual(list_decisions(path=self.db_path), [reloaded])

    def test_one_decision_per_report_id(self):
        original = save_decision(_sample_record("report-1"), path=self.db_path)
        with self.assertRaises(AuditStoreError):
            save_decision(
                _sample_record("report-1", decision="REJECTED", outcome="no"),
                path=self.db_path,
            )
        decisions = list_decisions(path=self.db_path)
        self.assertEqual(decisions, [original])
        self.assertEqual(decisions[0]["decision"], "APPROVED")

    def test_sqlite_operational_error_is_reported_without_exposing_database_details(self):
        with patch("audit_store.sqlite3.connect", side_effect=sqlite3.OperationalError("locked")):
            with self.assertRaisesRegex(
                AuditStoreError, "Unable to initialize the local audit database"
            ):
                initialize_database(path=self.db_path)

    def test_refuses_secret_bearing_fields(self):
        with self.assertRaises(AuditStoreError):
            save_decision(
                _sample_record(api_key="should-not-store"),
                path=self.db_path,
            )
        self.assertEqual(list_decisions(path=self.db_path), [])

    def test_guardbee_audit_db_env_override(self):
        previous = os.environ.get("GUARDBEE_AUDIT_DB")
        os.environ["GUARDBEE_AUDIT_DB"] = str(self.db_path)
        try:
            save_decision(_sample_record("env-report"))
            self.assertTrue(self.db_path.is_file())
            self.assertEqual(
                get_decision_by_report_id("env-report")["report_id"], "env-report"
            )
        finally:
            if previous is None:
                os.environ.pop("GUARDBEE_AUDIT_DB", None)
            else:
                os.environ["GUARDBEE_AUDIT_DB"] = previous

    def test_workflow_record_includes_required_audit_fields(self):
        incident = {"id": "INC-1", "events": [{"id": "EVT-1"}]}
        analysis = {"risk_score": 40, "evidence_ids": ["EVT-1"]}
        policies = [{"id": "POL-1"}]
        context_id = analysis_context_id(incident, analysis, policies)
        record = build_decision_record(
            "INC-1",
            "APPROVED",
            "simulated",
            "report body",
            context_id,
            context_id,
            "report-42",
            None,
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            evidence_ids=["EVT-1"],
            policy_ids=["POL-1"],
        )
        self.assertIsNotNone(record)
        for key in (
            "time_utc",
            "incident_id",
            "decision",
            "report_id",
            "report_context_id",
            "evidence_ids",
            "policy_ids",
            "status",
        ):
            self.assertIn(key, record)
        stored = save_decision(record, path=self.db_path)
        self.assertEqual(stored["evidence_ids"], ["EVT-1"])
        self.assertEqual(stored["policy_ids"], ["POL-1"])


if __name__ == "__main__":
    unittest.main()
