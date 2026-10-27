import unittest

from ui_presentation import (
    FILTER_ALL,
    FILTER_INSUFFICIENT,
    FILTER_NORMAL,
    FILTER_SUSPICIOUS,
    classification_counts,
    classification_of,
    filter_incidents_by_classification,
    format_severity,
    incident_option_label,
    matches_classification_filter,
)


class TestUiPresentation(unittest.TestCase):
    def test_format_severity_hides_none(self):
        self.assertEqual(format_severity("HIGH"), "HIGH")
        self.assertEqual(format_severity("MEDIUM"), "MEDIUM")
        self.assertEqual(format_severity("LOW"), "LOW")
        self.assertEqual(format_severity(None), "N/A")
        self.assertEqual(format_severity("None"), "N/A")

    def test_filter_separates_classifications(self):
        incidents = [
            {"id": "INC-S", "title": "s"},
            {"id": "INC-N", "title": "n"},
            {"id": "INC-I", "title": "i"},
        ]
        analyses = {
            "INC-S": {"classification": FILTER_SUSPICIOUS},
            "INC-N": {"classification": FILTER_NORMAL},
            "INC-I": {"classification": FILTER_INSUFFICIENT},
        }
        self.assertEqual(
            [i["id"] for i in filter_incidents_by_classification(incidents, analyses, FILTER_SUSPICIOUS)],
            ["INC-S"],
        )
        self.assertEqual(
            [i["id"] for i in filter_incidents_by_classification(incidents, analyses, FILTER_NORMAL)],
            ["INC-N"],
        )
        self.assertEqual(
            [i["id"] for i in filter_incidents_by_classification(incidents, analyses, FILTER_INSUFFICIENT)],
            ["INC-I"],
        )
        self.assertEqual(
            len(filter_incidents_by_classification(incidents, analyses, FILTER_ALL)),
            3,
        )

    def test_normal_is_not_matched_by_suspicious_filter(self):
        self.assertFalse(matches_classification_filter(FILTER_NORMAL, FILTER_SUSPICIOUS))
        self.assertTrue(matches_classification_filter(FILTER_SUSPICIOUS, FILTER_SUSPICIOUS))

    def test_counts_and_labels(self):
        analyses = {
            "A": {"classification": FILTER_SUSPICIOUS},
            "B": {"classification": FILTER_NORMAL},
            "C": {"classification": FILTER_INSUFFICIENT},
            "D": {"classification": FILTER_NORMAL},
        }
        self.assertEqual(
            classification_counts(analyses),
            {FILTER_SUSPICIOUS: 1, FILTER_NORMAL: 2, FILTER_INSUFFICIENT: 1},
        )
        label = incident_option_label(
            {"id": "INC-N", "title": "Known login"},
            {"classification": FILTER_NORMAL},
        )
        self.assertIn("[NORMAL]", label)
        self.assertEqual(classification_of({"classification": FILTER_SUSPICIOUS}), FILTER_SUSPICIOUS)


if __name__ == "__main__":
    unittest.main()
