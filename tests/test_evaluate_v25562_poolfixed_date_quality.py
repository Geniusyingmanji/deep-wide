from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import evaluate_v25562_poolfixed_date_quality as target  # noqa: E402


def pypi_payload(
    identity: str,
    *,
    release_date: str = "2026-01-01",
    unknown: bool = False,
) -> bytes:
    releases = (
        {"2.0rc1": [{"upload_time_iso_8601": f"{release_date}T00:00:00Z"}]}
        if unknown
        else {
            "1.0": [{"upload_time_iso_8601": "2025-01-01T00:00:00Z"}],
            "2.0": [{"upload_time_iso_8601": f"{release_date}T00:00:00Z"}],
            "3.0rc1": [{"upload_time_iso_8601": "2027-01-01T00:00:00Z"}],
        }
    )
    return json.dumps(
        {"info": {"name": identity}, "releases": releases}, sort_keys=True
    ).encode()


def complete_truth(
    *, unknown_indices: set[int] | None = None
) -> dict[str, dict[str, object]]:
    unknown_indices = unknown_indices or set()
    output: dict[str, dict[str, object]] = {}
    for index, identity in enumerate(target.contract.population.identity_vector()):
        day = 28 - (index % 20)
        output[identity] = target.total_truth.parse_response(
            pypi_payload(
                identity,
                release_date=f"2026-01-{day:02d}",
                unknown=index in unknown_indices,
            ),
            identity,
        )
    return output


def table(first: str, first_value: str, second: str, second_value: str) -> str:
    return (
        "| Package | Latest Stable Release Date |\n"
        "|---|---|\n"
        f"| {first} | {first_value} |\n"
        f"| {second} | {second_value} |"
    )


def metric_aggregate(*, exact_delta: int = 1, composite_delta: float = 0.0):
    control = {
        "tasks": 20,
        "valid_tasks": 20,
        "invalid_tasks": 0,
        "fallback_tasks": 0,
        "exact_table_successes": 5,
        "entity_coverage": 0.8,
        "row_f1": 0.6,
        "item_f1": 0.7,
        "column_f1": 1.0,
        "quality_composite": 0.775,
    }
    candidate = copy.deepcopy(control)
    candidate["exact_table_successes"] += exact_delta
    candidate["quality_composite"] += composite_delta
    return {
        "evaluation_count": 40,
        "truth_identity_count": 40,
        "truth_complete_tasks": 20,
        "arms": {target.BASE_ARM: control, target.CANDIDATE_ARM: candidate},
        "candidate_minus_control": target._delta(candidate, control),
        "candidate_vs_control_exact_disposition": {
            "candidate_win": max(0, exact_delta),
            "tie": 20 - abs(exact_delta),
            "candidate_loss": max(0, -exact_delta),
        },
        "candidate_vs_control_composite_disposition": {
            "candidate_win": int(composite_delta > 0),
            "tie": 20 - int(composite_delta != 0),
            "candidate_loss": int(composite_delta < 0),
        },
        "family_metrics": {},
        "shared_parent_treatment_comparison": True,
    }


class V25562PoolfixedDateQualityTests(unittest.TestCase):
    def test_endpoint_vector_is_fixed_unique_forty_pypi(self) -> None:
        values = target.endpoint_vector()
        self.assertEqual(len(values), 40)
        self.assertEqual([row["index"] for row in values], list(range(40)))
        self.assertEqual(len({row["identity"] for row in values}), 40)
        self.assertEqual({row["source"] for row in values}, {"pypi"})

    def test_semantic_value_accepts_unknown_and_equivalent_dates(self) -> None:
        self.assertEqual(target._semantic_value("unknown"), ("unknown", None))
        self.assertEqual(target._semantic_value("2026年3月1日"), ("date", "2026-03-01"))
        self.assertEqual(target._semantic_value("2026-03-01"), ("date", "2026-03-01"))
        self.assertIsNone(target._semantic_value("not established"))

    def test_known_dates_require_canonical_descending_order_for_exact(self) -> None:
        truth = complete_truth()
        first, second = target.contract.population.pair_vector()[0]
        first_value = str(truth[first]["canonical_value"])
        second_value = str(truth[second]["canonical_value"])
        canonical = table(first, first_value, second, second_value)
        reversed_rows = table(second, second_value, first, first_value)
        equivalent = canonical.replace("年", "-").replace("月", "-").replace("日", "")
        self.assertEqual(target.evaluate_prediction(canonical, 0, truth)["exact_table_success"], 1)
        reversed_metric = target.evaluate_prediction(reversed_rows, 0, truth)
        self.assertEqual(reversed_metric["exact_table_success"], 0)
        self.assertEqual(reversed_metric["quality_composite"], 1.0)
        equivalent_metric = target.evaluate_prediction(equivalent, 0, truth)
        self.assertEqual(equivalent_metric["exact_table_success"], 0)
        self.assertEqual(equivalent_metric["row_f1"], 1.0)

    def test_known_precedes_valid_unknown_for_exact(self) -> None:
        truth = complete_truth(unknown_indices={1})
        first, second = target.contract.population.pair_vector()[0]
        canonical = table(first, str(truth[first]["canonical_value"]), second, "Unknown")
        wrong_order = table(second, "Unknown", first, str(truth[first]["canonical_value"]))
        self.assertEqual(target.evaluate_prediction(canonical, 0, truth)["exact_table_success"], 1)
        metric = target.evaluate_prediction(wrong_order, 0, truth)
        self.assertEqual(metric["exact_table_success"], 0)
        self.assertEqual(metric["row_f1"], 1.0)

    def test_two_unknown_rows_preserve_supplied_order_for_exact(self) -> None:
        truth = complete_truth(unknown_indices={0, 1})
        first, second = target.contract.population.pair_vector()[0]
        canonical = table(first, "Unknown", second, "Unknown")
        reversed_rows = table(second, "Unknown", first, "Unknown")
        self.assertEqual(target.evaluate_prediction(canonical, 0, truth)["exact_table_success"], 1)
        metric = target.evaluate_prediction(reversed_rows, 0, truth)
        self.assertEqual(metric["exact_table_success"], 0)
        self.assertEqual(metric["quality_composite"], 1.0)

    def test_quality_gate_requires_exact_gain_nonregression_and_complete_truth(self) -> None:
        passing = metric_aggregate()
        self.assertTrue(target.quality_decision(passing)["quality_gate_passed"])
        for kind in ("exact", "soft", "truth", "invalid"):
            changed = copy.deepcopy(passing)
            if kind == "exact":
                changed["candidate_minus_control"]["exact_table_successes"] = 0
            elif kind == "soft":
                changed["candidate_minus_control"]["row_f1"] = -0.01
            elif kind == "truth":
                changed["truth_complete_tasks"] = 19
            else:
                changed["candidate_minus_control"]["invalid_tasks"] = 1
            with self.subTest(kind=kind):
                self.assertFalse(target.quality_decision(changed)["quality_gate_passed"])

    def test_frozen_rows_evaluate_all_forty_once(self) -> None:
        metrics = target.evaluate_rows(target._read_rows(), complete_truth())
        self.assertEqual(metrics["evaluation_count"], 40)
        self.assertEqual(metrics["truth_identity_count"], 40)
        self.assertEqual(metrics["truth_complete_tasks"], 20)
        self.assertEqual(metrics["arms"][target.BASE_ARM]["tasks"], 20)
        self.assertEqual(metrics["arms"][target.CANDIDATE_ARM]["tasks"], 20)

    def test_truth_snapshot_replays_total_unknown_and_tamper_fails(self) -> None:
        fetched = []
        for spec in target.endpoint_vector():
            fetched.append(
                {
                    **spec,
                    "attempt_count": 1,
                    "http_status": 200,
                    "transport_failure_type": None,
                    "raw": pypi_payload(
                        spec["identity"], unknown=spec["index"] == 0
                    ),
                }
            )
        compressed, value = target._truth_artifact(fetched, now=1)
        self.assertEqual(value["valid_unknown_record_count"], 1)
        self.assertEqual(target.validate_truth(value, compressed), value)
        changed = bytearray(compressed)
        changed[-1] ^= 1
        with self.assertRaises(ValueError):
            target.validate_truth(value, bytes(changed))

    def test_invalid_truth_is_absent_and_scores_zero_for_both_arms(self) -> None:
        fetched = []
        for spec in target.endpoint_vector():
            raw = pypi_payload(spec["identity"])
            if spec["index"] == 0:
                raw = b"not-json"
            fetched.append(
                {
                    **spec,
                    "attempt_count": 1,
                    "http_status": 200,
                    "transport_failure_type": None,
                    "raw": raw,
                }
            )
        compressed, truth = target._truth_artifact(fetched, now=1)
        target.validate_truth(truth, compressed)
        self.assertEqual(truth["valid_record_count"], 39)
        self.assertEqual(truth["complete_task_count"], 19)
        metrics = target.evaluate_rows(target._read_rows(), truth["records"])
        self.assertEqual(metrics["truth_complete_tasks"], 19)
        self.assertEqual(metrics["arms"][target.BASE_ARM]["invalid_tasks"], 1)
        self.assertEqual(metrics["arms"][target.CANDIDATE_ARM]["invalid_tasks"], 1)

    def test_result_is_sealed_zero_credit_and_no_benchmark_authorization(self) -> None:
        truth = {
            "compressed_snapshot_sha256": "b" * 64,
            "truth_payload_sha256": "c" * 64,
            "attempt_count": 40,
            "valid_unknown_record_count": 2,
        }
        protocol = {
            "forward_audit_sha256": target.FORWARD_AUDIT_SHA256,
            "forward_result_sha256": target.FORWARD_RESULT_SHA256,
            "task_rows_sha256": target.TASK_ROWS_SHA256,
            "prediction_freeze_sha256": target.PREDICTION_FREEZE_SHA256,
        }
        value = target._result_artifact(
            protocol, truth, metric_aggregate(), now=1, protocol_sha256="a" * 64
        )
        self.assertEqual(
            target.validate_result(value, expected_protocol_sha256="a" * 64), value
        )
        self.assertEqual(value["positive_signed_credit_count"], 0)
        self.assertFalse(value["authorization"]["deepwidebench_forward_or_evaluator"])

    def test_build_audit_only_authorizes_protocol_and_network_contract_is_one_shot(self) -> None:
        tests = {
            "expected": 17,
            "observed": 17,
            "passed": True,
            "suites": [
                {
                    "pattern": target.TEST.name,
                    "expected": 11,
                    "observed": 11,
                    "returncode": 0,
                    "passed": True,
                    "output_sha256": hashlib.sha256(b"ok").hexdigest(),
                },
                {
                    "pattern": target.TRUTH_TEST.name,
                    "expected": 6,
                    "observed": 6,
                    "returncode": 0,
                    "passed": True,
                    "output_sha256": hashlib.sha256(b"ok2").hexdigest(),
                },
            ],
        }
        self.assertTrue(target._source_network_contract(ROOT / target.SOURCE))
        with (
            mock.patch.object(target, "_tests", return_value=tests),
            mock.patch.object(target, "_future_pristine", return_value=True),
            mock.patch.object(target, "_active_conflicts", return_value=[]),
            mock.patch.object(target.forward_control, "_lease_inactive", return_value=True),
        ):
            value = target.build_audit(now=1, require_clean=False)
        self.assertEqual(target.validate_build_audit(value), value)
        self.assertTrue(
            value["authorization"]["postfreeze_quality_protocol_generation"]
        )
        self.assertFalse(value["authorization"]["one_truth_fetch_or_quality_evaluation"])


if __name__ == "__main__":
    unittest.main()
