import unittest
from datetime import datetime, timezone

from workflow import analysis_context_id, build_decision_record, can_record_decision


class TestDecisionWorkflow(unittest.TestCase):
    def setUp(self):
        self.incident = {"id": "INC-1", "events": [{"id": "EVT-1"}]}
        self.analysis = {"risk_score": 40, "evidence_ids": ["EVT-1"]}
        self.policies = [{"id": "POL-1"}]
        self.context_id = analysis_context_id(self.incident, self.analysis, self.policies)

    def test_approve_blocks_duplicate_and_conflicting_decision(self):
        record = build_decision_record(
            "INC-1", "APPROVED", "simulated", "report", self.context_id,
            self.context_id, "report-1", None, datetime(2026, 1, 1, tzinfo=timezone.utc),
            evidence_ids=["EVT-1"],
            policy_ids=["POL-1"],
        )
        self.assertEqual(record["decision"], "APPROVED")
        self.assertEqual(record["evidence_ids"], ["EVT-1"])
        self.assertEqual(record["policy_ids"], ["POL-1"])
        self.assertEqual(record["status"], "RECORDED")
        self.assertEqual(record["report_context_id"], self.context_id)
        conflicting = build_decision_record(
            "INC-1", "REJECTED", "no action", "report", self.context_id,
            self.context_id, "report-1", record,
        )
        self.assertIsNone(conflicting)

    def test_reject_and_new_analysis_are_allowed_once_each(self):
        rejected = build_decision_record(
            "INC-1", "REJECTED", "no action", "report", self.context_id,
            self.context_id, "report-1", None,
        )
        self.assertEqual(rejected["decision"], "REJECTED")
        self.assertTrue(can_record_decision("new report", self.context_id, self.context_id, "report-2", rejected))

    def test_stale_report_context_cannot_authorize_decision(self):
        self.assertFalse(can_record_decision("report", "old-context", self.context_id, "report-1", None))

    def test_context_changes_when_retrieved_policy_changes(self):
        changed = analysis_context_id(self.incident, self.analysis, [{"id": "POL-2"}])
        self.assertNotEqual(self.context_id, changed)
