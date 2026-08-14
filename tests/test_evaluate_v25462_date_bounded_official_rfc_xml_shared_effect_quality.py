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

from scripts import evaluate_v25462_date_bounded_official_rfc_xml_shared_effect_quality as target  # noqa: E402


def fixture_xml(*, malformed_not_issued: bool = False) -> bytes:
    entries: list[str] = []
    for number in range(8920, 9000):
        if number == 8959:
            extra = "<title>Ambiguous</title>" if malformed_not_issued else ""
            entries.append(
                f"<rfc-not-issued-entry><doc-id>RFC{number}</doc-id>{extra}</rfc-not-issued-entry>"
            )
            continue
        entries.append(
            f"""
            <rfc-entry>
              <doc-id>RFC{number}</doc-id>
              <title>Title {number}</title>
              <author><name>A. Author{number}</name></author>
              <date><month>August</month><year>2026</year></date>
              <current-status>INFORMATIONAL</current-status>
              <publication-status>INFORMATIONAL</publication-status>
              <stream>IETF</stream>
            </rfc-entry>
            """
        )
    return (
        f'<rfc-index xmlns="{target.RFC_INDEX_NAMESPACE}">'
        + "".join(entries)
        + "</rfc-index>"
    ).encode()


def arm(value: float, *, exact: int, invalid: int = 0) -> dict:
    return {
        "tasks": 20,
        "valid_tasks": 20 - invalid,
        "invalid_tasks": invalid,
        "fallback_tasks": 0,
        "exact_table_successes": exact,
        "entity_coverage": value,
        "row_exact": value,
        "cell_accuracy": value,
        "column_accuracy": value,
        "quality_composite": value,
    }


def gate_metrics(*, base: dict, candidate: dict) -> dict:
    return {
        "evaluation_count": 40,
        "arms": {
            target.BASE_ARM: base,
            target.CANDIDATE_ARM: candidate,
        },
        "candidate_minus_base": target._delta(candidate, base),
        "candidate_vs_base_exact_disposition": {
            "candidate_win": 1,
            "tie": 19,
            "candidate_loss": 0,
        },
        "candidate_vs_base_composite_disposition": {
            "candidate_win": 1,
            "tie": 19,
            "candidate_loss": 0,
        },
        "shared_parent_treatment_comparison": True,
    }


class V25462DateBoundedOfficialXmlSharedEffectQualityTests(unittest.TestCase):
    def test_parser_handles_namespace_and_structural_not_issued(self) -> None:
        records, not_issued = target.parse_rfc_index(
            fixture_xml(), tuple(range(8920, 9000))
        )
        self.assertEqual(len(records), 80)
        self.assertEqual(not_issued, ("RFC 8959",))
        self.assertEqual(
            records["RFC 8959"],
            {
                "RFC": "RFC 8959",
                "Title": "Unknown",
                "Authors": "Unknown",
                "Status": "Unknown",
                "Stream": "Unknown",
                "Published": "Unknown",
            },
        )

    def test_parser_rejects_wrong_namespace_ambiguous_and_missing(self) -> None:
        with self.assertRaises(ValueError):
            target.parse_rfc_index(
                fixture_xml().replace(
                    target.RFC_INDEX_NAMESPACE.encode(), b"urn:wrong"
                ),
                tuple(range(8920, 9000)),
            )
        with self.assertRaises(ValueError):
            target.parse_rfc_index(
                fixture_xml(malformed_not_issued=True), tuple(range(8920, 9000))
            )
        missing = fixture_xml().replace(
            b"<rfc-not-issued-entry><doc-id>RFC8959</doc-id></rfc-not-issued-entry>",
            b"",
        )
        with self.assertRaises(ValueError):
            target.parse_rfc_index(missing, tuple(range(8920, 9000)))

    def test_primary_gate_accepts_exact_gain_and_soft_nonregression(self) -> None:
        base = arm(0.8, exact=2)
        candidate = arm(0.81, exact=3)
        decision = target.quality_decision(
            gate_metrics(base=base, candidate=candidate)
        )
        self.assertTrue(decision["quality_gate_passed"])
        self.assertEqual(decision["failed_checks"], [])

    def test_primary_gate_requires_exact_gain_and_all_soft_nonregression(self) -> None:
        base = arm(0.8, exact=2)
        candidate = arm(0.79, exact=2)
        decision = target.quality_decision(
            gate_metrics(base=base, candidate=candidate)
        )
        self.assertFalse(decision["quality_gate_passed"])
        self.assertIn(
            "candidate_whole_table_exact_strict_gain", decision["failed_checks"]
        )
        self.assertIn(
            "candidate_quality_composite_nonregression",
            decision["failed_checks"],
        )

    def test_truth_artifact_replays_exact_snapshot_and_tamper_fails(self) -> None:
        raw = fixture_xml()
        records, not_issued = target.parse_rfc_index(
            raw, tuple(range(8920, 9000))
        )
        compressed, truth = target._truth_artifact(
            raw, 200, None, records, not_issued, now=1
        )
        self.assertEqual(target.validate_truth(truth, compressed), truth)
        changed = copy.deepcopy(truth)
        changed["not_issued_count"] = 0
        changed.pop("truth_payload_sha256")
        changed = target.contract.seal(changed, "truth_payload_sha256")
        with self.assertRaises(ValueError):
            target.validate_truth(changed, compressed)
        with self.assertRaises(ValueError):
            target.validate_truth(truth, gzip.compress(b"wrong", mtime=0))

    def test_result_is_sealed_zero_credit_and_never_directly_authorizes_220(self) -> None:
        base = arm(0.8, exact=2)
        candidate = arm(0.81, exact=3)
        metrics = gate_metrics(base=base, candidate=candidate)
        protocol = {
            "forward_audit_sha256": target.FORWARD_AUDIT_SHA256,
            "forward_result_sha256": target.FORWARD_RESULT_SHA256,
            "task_rows_sha256": target.TASK_ROWS_SHA256,
            "prediction_freeze_sha256": target.PREDICTION_FREEZE_SHA256,
        }
        truth = {
            "raw_response_sha256": "a" * 64,
            "compressed_snapshot_sha256": "b" * 64,
            "truth_payload_sha256": "c" * 64,
        }
        value = target._result_artifact(
            protocol,
            truth,
            metrics,
            now=1,
            protocol_sha256="d" * 64,
        )
        self.assertEqual(
            target.validate_result(value, expected_protocol_sha256="d" * 64),
            value,
        )
        self.assertEqual(value["positive_signed_credit_count"], 0)
        self.assertFalse(value["authorization"]["deepwidebench_successor_build"])

    def test_contract_fixes_single_fetch_two_arms_and_parser_before_truth(self) -> None:
        self.assertEqual(target.ARMS, target.forward_runner.ARMS)
        self.assertEqual(target.truth_fetch_contract()["maximum_attempts"], 1)
        self.assertEqual(target.truth_fetch_contract()["retries"], 0)
        self.assertEqual(
            target.scoring_contract()["primary_comparison"],
            "date_bounded_official_rfc_xml_record_candidate_minus_shared_base_table",
        )
        self.assertEqual(target.scoring_contract()["arms"], list(target.ARMS))
        self.assertTrue(target._source_network_contract(ROOT / target.SOURCE))

    def test_build_audit_authorizes_only_quality_protocol(self) -> None:
        test_result = {
            "pattern": target.TEST.name,
            "expected": target.EXPECTED_TESTS,
            "observed": target.EXPECTED_TESTS,
            "returncode": 0,
            "passed": True,
            "output_sha256": "a" * 64,
        }
        with mock.patch.object(
            target.forward_control, "_test", return_value=test_result
        ), mock.patch.object(
            target.base_audit, "_tracked", return_value=True
        ), mock.patch.object(
            target, "_future_pristine", return_value=True
        ), mock.patch.object(
            target, "_source_network_contract", return_value=True
        ):
            value = target.build_audit(now=1, require_clean=False)
        self.assertEqual(target.validate_build_audit(value), value)
        self.assertTrue(
            value["authorization"]["postfreeze_quality_protocol_generation"]
        )
        self.assertFalse(value["authorization"]["truth_fetch_or_evaluation"])
        self.assertFalse(
            value["authorization"]["deepwidebench_successor_build_or_forward"]
        )


if __name__ == "__main__":
    unittest.main()
