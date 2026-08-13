from __future__ import annotations

import copy
import gzip
import inspect
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25415_paired_rfc_route_external_contract as contract  # noqa: E402
from scripts import evaluate_v25416_paired_rfc_route_quality as scorer  # noqa: E402
from scripts import evaluate_v25417_rfc_namespace_snapshot_recovery as failed  # noqa: E402
from scripts import evaluate_v25418_rfc_not_issued_snapshot_recovery as target  # noqa: E402


def fixture_xml(*, malformed_not_issued=False) -> bytes:
    entries = []
    for offset, number in enumerate(range(9320, 9400)):
        if number == 9379:
            extra = "<title>Ambiguous</title>" if malformed_not_issued else ""
            entries.append(
                f"<rfc-not-issued-entry><doc-id>RFC9379</doc-id>{extra}</rfc-not-issued-entry>"
            )
            continue
        entries.append(
            f"""
            <rfc-entry>
              <doc-id>RFC{number:04d}</doc-id>
              <title>Title {offset}</title>
              <author><name>A. Author{offset}</name></author>
              <date><month>March</month><year>2022</year></date>
              <current-status>PROPOSED STANDARD</current-status>
              <publication-status>PROPOSED STANDARD</publication-status>
              <stream>IETF</stream>
            </rfc-entry>
            """
        )
    return (
        f'<rfc-index xmlns="{target.RFC_INDEX_NAMESPACE}">'
        + "".join(entries)
        + "</rfc-index>"
    ).encode()


class V25418RfcNotIssuedSnapshotRecoveryTests(unittest.TestCase):
    def test_parser_extracts_seventy_nine_records_and_one_not_issued(self) -> None:
        records, not_issued = target.parse_rfc_and_not_issued_index(
            fixture_xml(), tuple(range(9320, 9400))
        )
        self.assertEqual(len(records), 80)
        self.assertEqual(not_issued, ("RFC 9379",))
        self.assertEqual(
            records["RFC 9379"],
            {
                "RFC": "RFC 9379",
                "Title": "Unknown",
                "Authors": "Unknown",
                "Status": "Unknown",
                "Stream": "Unknown",
                "Published": "Unknown",
            },
        )

    def test_v25417_failure_is_reproduced_and_successor_is_total(self) -> None:
        raw = fixture_xml()
        with self.assertRaisesRegex(ValueError, "lacks a fixed truth record"):
            failed.parse_namespaced_rfc_index(raw, tuple(range(9320, 9400)))
        records, _ = target.parse_rfc_and_not_issued_index(
            raw, tuple(range(9320, 9400))
        )
        self.assertEqual(len(records), 80)

    def test_parser_rejects_ambiguous_not_issued_and_missing_identity(self) -> None:
        with self.assertRaises(ValueError):
            target.parse_rfc_and_not_issued_index(
                fixture_xml(malformed_not_issued=True), tuple(range(9320, 9400))
            )
        raw = fixture_xml().replace(
            b"<rfc-not-issued-entry><doc-id>RFC9379</doc-id></rfc-not-issued-entry>",
            b"",
        )
        with self.assertRaises(ValueError):
            target.parse_rfc_and_not_issued_index(raw, tuple(range(9320, 9400)))

    def test_offline_guards_deny_parent_fetch_and_restore_it(self) -> None:
        original = scorer._fetch_once
        with target._offline_guards():
            with self.assertRaises(RuntimeError):
                scorer._fetch_once()
        self.assertIs(scorer._fetch_once, original)

    def test_source_has_no_network_surface_and_paths_are_append_only(self) -> None:
        self.assertTrue(target._source_has_zero_network_surface(ROOT / target.SOURCE))
        source = inspect.getsource(target.replay)
        self.assertNotIn("_fetch_once(", source)
        self.assertNotEqual(target.RECOVERY_TRUTH, scorer.TRUTH)
        self.assertNotEqual(target.RECOVERY_TRUTH, failed.RECOVERY_TRUTH)
        self.assertNotEqual(target.RESULT, contract.QUALITY_RESULT)
        self.assertNotEqual(target.RESULT, failed.RESULT)

    def test_build_audit_authorizes_only_protocol_generation(self) -> None:
        test_result = {
            "pattern": target.TEST.name,
            "expected": target.EXPECTED_TESTS,
            "observed": target.EXPECTED_TESTS,
            "returncode": 0,
            "passed": True,
            "output_sha256": "a" * 64,
        }
        with mock.patch.object(target.base_audit, "_test", return_value=test_result), mock.patch.object(
            target.base_audit, "_tracked", return_value=True
        ), mock.patch.object(target, "_future_pristine", return_value=True):
            value = target.build_audit(now=1, require_clean=False)
        self.assertEqual(target.validate_build_audit(value), value)
        self.assertTrue(value["authorization"]["offline_recovery_protocol_generation"])
        self.assertFalse(value["authorization"]["snapshot_replay_or_quality_evaluation"])
        self.assertFalse(value["authorization"]["new_truth_fetch_model_search_or_deepwidebench"])

    def test_truth_artifact_replays_same_snapshot_and_tamper_fails(self) -> None:
        raw = fixture_xml()
        compressed = gzip.compress(raw, mtime=0)
        records, not_issued = target.parse_rfc_and_not_issued_index(
            raw, tuple(range(9320, 9400))
        )
        with mock.patch.object(target, "RAW_SNAPSHOT_SHA256", target.hashlib.sha256(compressed).hexdigest()), mock.patch.object(
            target, "RAW_RESPONSE_SHA256", target.hashlib.sha256(raw).hexdigest()
        ):
            value = target._truth_artifact(raw, records, not_issued, now=1)
            self.assertEqual(target.validate_truth(value, compressed), value)
            changed = copy.deepcopy(value)
            changed["not_issued_count"] = 0
            changed.pop("truth_payload_sha256")
            changed = contract.seal(changed, "truth_payload_sha256")
            with self.assertRaises(ValueError):
                target.validate_truth(changed, compressed)

    def test_not_issued_unknown_row_scores_exact_under_frozen_scorer(self) -> None:
        truth = {
            "RFC 9376": {"RFC": "RFC 9376", "Title": "A", "Authors": "Smith", "Status": "Informational", "Stream": "IETF", "Published": "March 2023"},
            "RFC 9377": {"RFC": "RFC 9377", "Title": "B", "Authors": "Jones", "Status": "Experimental", "Stream": "IETF", "Published": "April 2023"},
            "RFC 9378": {"RFC": "RFC 9378", "Title": "C", "Authors": "Brown", "Status": "Informational", "Stream": "IETF", "Published": "April 2023"},
            "RFC 9379": {"RFC": "RFC 9379", "Title": "Unknown", "Authors": "Unknown", "Status": "Unknown", "Stream": "Unknown", "Published": "Unknown"},
        }
        rows = [
            "| RFC 9376 | A | Smith | Informational | IETF | March 2023 |",
            "| RFC 9377 | B | Jones | Experimental | IETF | April 2023 |",
            "| RFC 9378 | C | Brown | Informational | IETF | April 2023 |",
            "| RFC 9379 | Unknown | Unknown | Unknown | Unknown | Unknown |",
        ]
        prediction = (
            "| RFC | Title | Authors | Status | Stream | Published |\n"
            "| --- | --- | --- | --- | --- | --- |\n" + "\n".join(rows)
        )
        metric = scorer.evaluate_prediction(
            prediction,
            ("RFC 9376", "RFC 9377", "RFC 9378", "RFC 9379"),
            truth,
        )
        self.assertEqual(metric["exact_table_success"], 1)
        self.assertEqual(metric["quality_composite"], 1.0)


if __name__ == "__main__":
    unittest.main()
