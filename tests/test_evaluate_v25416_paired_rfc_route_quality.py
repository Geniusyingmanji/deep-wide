from __future__ import annotations

import copy
import gzip
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25411_visible_membership_route_runtime as route  # noqa: E402
from deepwide_agent import v25415_paired_rfc_route_external_contract as contract  # noqa: E402
from scripts import evaluate_v25416_paired_rfc_route_quality as target  # noqa: E402


def fixture_xml(numbers=(9320, 9321, 9322, 9323)) -> bytes:
    entries = []
    for offset, number in enumerate(numbers):
        entries.append(
            f"""
            <rfc-entry>
              <doc-id>RFC{number:04d}</doc-id>
              <title>Title {offset}</title>
              <author><name>A. Author{offset}</name></author>
              <author><name>B. Editor{offset}, Ed.</name></author>
              <date><month>March</month><year>2022</year></date>
              <current-status>PROPOSED STANDARD</current-status>
              <publication-status>PROPOSED STANDARD</publication-status>
              <stream>IETF</stream>
            </rfc-entry>
            """
        )
    return ("<rfc-index>" + "".join(entries) + "</rfc-index>").encode()


def truth(numbers=(9320, 9321, 9322, 9323)):
    return target.parse_rfc_index(fixture_xml(numbers), numbers)


def prediction(numbers=(9320, 9321, 9322, 9323), *, wrong=False):
    rows = []
    for offset, number in enumerate(numbers):
        title = "Wrong" if wrong and offset == 0 else f"Title {offset}"
        rows.append(
            f"| RFC {number:04d} | {title} | A. Author{offset}; B. Editor{offset}, Ed. | Proposed Standard | Internet Engineering Task Force (IETF) | 2022-03 |"
        )
    return (
        "```markdown\n| RFC | Title | Authors | Status | Stream | Published |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        + "\n".join(rows)
        + "\n```"
    )


class V25416PairedRfcRouteQualityTests(unittest.TestCase):
    def test_xml_parser_extracts_fixed_records_and_rejects_duplicate_or_missing(self) -> None:
        value = truth()
        self.assertEqual(list(value), ["RFC 9320", "RFC 9321", "RFC 9322", "RFC 9323"])
        self.assertEqual(value["RFC 9320"]["Title"], "Title 0")
        self.assertEqual(value["RFC 9320"]["Published"], "March 2022")
        with self.assertRaises(ValueError):
            target.parse_rfc_index(
                fixture_xml((9320, 9320)), (9320,)
            )
        broken = fixture_xml().replace(b"<stream>IETF</stream>", b"", 1)
        with self.assertRaises(ValueError):
            target.parse_rfc_index(broken, (9320, 9321, 9322, 9323))

    def test_field_normalizers_are_fixed_and_not_substring_matching(self) -> None:
        self.assertTrue(target._field_equal("Authors", "A. Smith; B. Jones, Ed.", "Alice Smith; Bob Jones"))
        self.assertTrue(target._field_equal("Authors", "A. Smith, B. Jones", "Alice Smith; Bob Jones"))
        self.assertTrue(target._field_equal("Stream", "Internet Engineering Task Force (IETF)", "IETF"))
        self.assertTrue(target._field_equal("Stream", "Independent Submission", "INDEPENDENT"))
        self.assertTrue(target._field_equal("Published", "2022-03", "March 2022"))
        self.assertTrue(target._field_equal("Status", "Proposed Standard", "PROPOSED STANDARD"))
        self.assertFalse(target._field_equal("Title", "A title extension", "A title"))
        self.assertFalse(target._field_equal("Authors", "A. Smith", "A. Smith; B. Jones"))

    def test_exact_prediction_gets_all_metrics_one_and_one_cell_error_is_local(self) -> None:
        identities = ("RFC 9320", "RFC 9321", "RFC 9322", "RFC 9323")
        exact = target.evaluate_prediction(prediction(), identities, truth())
        self.assertTrue(exact["valid"])
        self.assertEqual(exact["exact_table_success"], 1)
        for name in target.METRICS:
            self.assertEqual(exact[name], 1.0)
        changed = target.evaluate_prediction(prediction(wrong=True), identities, truth())
        self.assertEqual(changed["exact_table_success"], 0)
        self.assertEqual(changed["entity_coverage"], 1.0)
        self.assertEqual(changed["row_exact"], 0.75)
        self.assertEqual(changed["cell_accuracy"], 19 / 20)

    def test_invalid_schema_duplicate_or_missing_truth_is_failure_as_zero(self) -> None:
        identities = ("RFC 9320", "RFC 9321", "RFC 9322", "RFC 9323")
        values = (
            "not a table",
            prediction().replace("RFC 9323", "RFC 9322"),
        )
        for value in values:
            metric = target.evaluate_prediction(value, identities, truth())
            self.assertFalse(metric["valid"])
            self.assertEqual(metric["quality_composite"], 0.0)
        partial = truth()
        partial.pop("RFC 9323")
        metric = target.evaluate_prediction(prediction(), identities, partial)
        self.assertFalse(metric["valid"])
        self.assertEqual(metric["exact_table_success"], 0)

    def test_quality_decision_requires_exact_gain_and_all_nonregression(self) -> None:
        branch = {
            "tasks": 20,
            "valid_tasks": 20,
            "invalid_tasks": 0,
            "fallback_tasks": 0,
            "exact_table_successes": 1,
            **{name: 0.5 for name in target.METRICS},
        }
        metrics = {
            "branches": {
                route.STABLE_BRANCH: branch,
                route.MEMBERSHIP_BRANCH: {**branch, "exact_table_successes": 2},
            },
            "membership_present_minus_absent": {
                "exact_table_successes": 1,
                "valid_tasks": 0,
                "invalid_tasks": 0,
                "fallback_tasks": 0,
                **{name: 0.0 for name in target.METRICS},
            },
            "paired_exact_disposition": {"present_win": 1, "tie": 19, "present_loss": 0},
            "paired_composite_disposition": {"present_win": 0, "tie": 20, "present_loss": 0},
        }
        self.assertTrue(target.quality_decision(metrics)["quality_gate_passed"])
        for field in ("exact_table_successes", *target.METRICS):
            changed = copy.deepcopy(metrics)
            changed["membership_present_minus_absent"][field] = 0 if field == "exact_table_successes" else -0.01
            with self.subTest(field=field):
                self.assertFalse(target.quality_decision(changed)["quality_gate_passed"])

    def test_truth_artifact_replays_compressed_snapshot_and_tamper_fails(self) -> None:
        raw = fixture_xml()
        compressed = gzip.compress(raw, mtime=0)
        records = target.parse_rfc_index(raw, (9320, 9321, 9322, 9323))
        value = contract.seal(
            {
                "artifact_version": 1,
                "role": "v25416_postfreeze_official_rfc_truth",
                "protocol_id": contract.PROTOCOL_ID,
                "created_at_unix": 1,
                "official_truth_url": target.URL,
                "attempt_count": 1,
                "http_status": 200,
                "fetch_or_parse_failure_type": None,
                "raw_response_bytes": len(raw),
                "raw_response_sha256": target.hashlib.sha256(raw).hexdigest(),
                "compressed_snapshot_sha256": target.hashlib.sha256(compressed).hexdigest(),
                "expected_identity_count": 80,
                "valid_record_count": len(records),
                "records": records,
                "one_attempt_no_redirect_retry_refetch_or_replacement": True,
                "same_snapshot_used_for_both_route_branches": True,
                "prediction_freeze_preexisted": True,
            },
            "truth_payload_sha256",
        )
        with mock.patch.object(
            target.contract.population, "RFC_NUMBERS", tuple(range(9320, 9324))
        ):
            self.assertEqual(target.validate_truth(value, compressed), value)
            changed = copy.deepcopy(value)
            changed["attempt_count"] = 2
            changed.pop("truth_payload_sha256")
            changed = contract.seal(changed, "truth_payload_sha256")
            with self.assertRaises(ValueError):
                target.validate_truth(changed, compressed)

    def test_fetch_once_is_one_redirect_disabled_no_retry_call(self) -> None:
        response = mock.Mock(status_code=200, content=fixture_xml())
        with mock.patch.object(target.requests, "get", return_value=response) as get:
            raw, status, failure = target._fetch_once()
        self.assertEqual(raw, fixture_xml())
        self.assertEqual(status, 200)
        self.assertIsNone(failure)
        self.assertEqual(get.call_count, 1)
        self.assertFalse(get.call_args.kwargs["allow_redirects"])

    def test_build_audit_and_protocol_never_authorize_truth_or_benchmark(self) -> None:
        with mock.patch.object(target.base_audit, "_test", return_value={
            "pattern": target.TEST.name,
            "expected": target.EXPECTED_TESTS,
            "observed": target.EXPECTED_TESTS,
            "returncode": 0,
            "passed": True,
            "output_sha256": "a" * 64,
        }), mock.patch.object(
            target,
            "_forward_barrier",
            return_value=({"audit_valid": True}, [{}] * 40),
        ), mock.patch.object(
            target.base_audit, "_tracked", return_value=True
        ):
            value = target.build_audit(now=1, require_clean=False)
        self.assertEqual(target.validate_build_audit(value), value)
        self.assertFalse(value["authorization"]["truth_fetch_or_evaluation"])
        self.assertFalse(value["authorization"]["deepwidebench_successor_build_or_forward"])


if __name__ == "__main__":
    unittest.main()
