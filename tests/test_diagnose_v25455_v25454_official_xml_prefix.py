from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v25455_v25454_official_xml_prefix as target  # noqa: E402


class V25455OfficialXmlPrefixDiagnosisTests(unittest.TestCase):
    def test_frozen_prefix_statistics_and_barriers_are_exact(self) -> None:
        value = target.build_diagnosis(now=1, require_clean=False)
        self.assertEqual(value["aggregate_prefix_statistics"], target.EXPECTED_STATS)
        self.assertEqual(
            value["complete_author_count_histogram"],
            target.EXPECTED_AUTHOR_HISTOGRAM,
        )
        self.assertFalse(value["forward_status"]["mechanism_gate_passed"])
        self.assertFalse(
            value["forward_status"]["postfreeze_quality_protocol_authorized"]
        )

    def test_date_bounded_closure_accepts_complete_front_prefix(self) -> None:
        content = (
            '<rfc number="9000" category="std">'
            "<front><title>A</title>"
            '<seriesInfo name="RFC" value="9000" stream="IETF"/>'
            '<author initials="A." surname="B"><organization>X</organization></author>'
            '<date month="05" year="2021"/>'
            "<abstract><t>truncated"
        )
        document = target._date_bounded_document(content)
        self.assertIsNotNone(document)
        self.assertTrue(document.endswith("</front></rfc>"))

    def test_date_bounded_closure_rejects_unsafe_or_incomplete_prefix(self) -> None:
        for content in (
            '<!DOCTYPE rfc><rfc><front><date year="2021"/>',
            '<rfc><front><author initials="A." surname="B"><date year="2021"/>',
            '<rfc><front><author initials="A." surname="B"/></front>',
        ):
            with self.subTest(content=content):
                self.assertIsNone(target._date_bounded_document(content))

    def test_resealed_stats_or_authorization_tamper_fails(self) -> None:
        value = target.build_diagnosis(now=1, require_clean=False)
        for kind in ("stats", "authorization"):
            changed = copy.deepcopy(value)
            if kind == "stats":
                changed["aggregate_prefix_statistics"][
                    "date_bounded_parseable_record_count"
                ] = 77
            else:
                changed["authorization"]["new_external_forward"] = True
            changed.pop("diagnosis_payload_sha256")
            changed["diagnosis_payload_sha256"] = target.contract.payload_sha256(
                changed
            )
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_diagnosis(changed)


if __name__ == "__main__":
    unittest.main()
