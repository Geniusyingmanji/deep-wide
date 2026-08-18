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

from scripts import evaluate_v25580_fresh_canonical_totality_quality as target  # noqa: E402


def pypi_payload(
    identity: str,
    *,
    version: str = "2.0",
    unknown: bool = False,
) -> bytes:
    releases = (
        {"3.0rc1": [{}], "4.0.dev1": [{}]}
        if unknown
        else {"1.0": [{}], version: [{}], "3.0rc1": [{}]}
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
        output[identity] = target.total_truth.parse_response(
            pypi_payload(
                identity,
                version=f"2.{index + 1}",
                unknown=index in unknown_indices,
            ),
            identity,
        )
    return output


def table(index: int, rows: list[tuple[str, str]]) -> str:
    columns = target.contract.population.columns_for_index(index)
    return (
        "| "
        + " | ".join(columns)
        + " |\n|---|---|\n"
        + "\n".join(f"| {identity} | {value} |" for identity, value in rows)
    )


def metric_aggregate(
    *, exact_delta: int = 6, complete_tasks: int = 20, losses: int = 0
) -> dict[str, object]:
    control = {
        "tasks": 20,
        "valid_tasks": 10,
        "invalid_tasks": 10,
        "fallback_tasks": 10,
        "exact_table_successes": 0,
        "entity_coverage": 0.5,
        "row_f1": 0.0,
        "item_f1": 0.25,
        "column_f1": 0.5,
        "quality_composite": 0.3125,
    }
    candidate = copy.deepcopy(control)
    candidate.update(
        {
            "valid_tasks": 20,
            "invalid_tasks": 0,
            "fallback_tasks": 0,
            "exact_table_successes": exact_delta,
            "entity_coverage": 1.0,
            "row_f1": 0.7,
            "item_f1": 0.85,
            "column_f1": 1.0,
            "quality_composite": 0.8875,
        }
    )
    return {
        "evaluation_count": 40,
        "truth_identity_count": 40,
        "truth_complete_tasks": complete_tasks,
        "arms": {target.CONTROL_ARM: control, target.CANDIDATE_ARM: candidate},
        "candidate_minus_control": target._delta(candidate, control),
        "candidate_vs_control_exact_disposition": {
            "candidate_win": exact_delta,
            "tie": 20 - exact_delta - losses,
            "candidate_loss": losses,
        },
        "candidate_vs_control_composite_disposition": {
            "candidate_win": 10,
            "tie": 10,
            "candidate_loss": 0,
        },
        "arm_blind_paired_complete_exact": {
            "candidate_win": exact_delta,
            "tie": complete_tasks - exact_delta - losses,
            "candidate_loss": losses,
            "task_count": complete_tasks,
            "discordant_task_count": exact_delta + losses,
            "two_sided_exact_sign_test_p": target._two_sided_exact_sign_test(
                exact_delta, losses
            ),
        },
        "paired_complete_selection": {
            "selected_task_count": complete_tasks,
            "selection_signal": "both_frozen_official_truth_records_valid",
            "prediction_arm_outcome_or_score_used": False,
            "task_identity_question_prediction_or_score_persisted": False,
        },
        "family_metrics": {},
        "ordinary_negative_control_prediction_count": 10,
        "ordinary_negative_control_predictions_byte_equal": 10,
        "same_forward_provider_retrieval_and_sampling_effects": True,
        "shared_parent_totality_recovery_comparison": True,
    }


class V25580FreshCanonicalTotalityQualityTests(unittest.TestCase):
    def test_endpoint_vector_is_fixed_unique_forty_pypi(self) -> None:
        values = target.endpoint_vector()
        self.assertEqual(len(values), 40)
        self.assertEqual([row["index"] for row in values], list(range(40)))
        self.assertEqual(len({row["identity"] for row in values}), 40)
        self.assertEqual({row["source"] for row in values}, {"pypi"})

    def test_semantic_value_accepts_pep440_equivalence_and_unknown(self) -> None:
        self.assertEqual(target._semantic_value("unknown"), ("unknown", None))
        self.assertEqual(
            target._semantic_value("1.0.0"),
            ("version", target.total_truth.semantic_version("1.0")),
        )
        self.assertEqual(
            target.total_truth.semantic_version("1.0.0"),
            target.total_truth.semantic_version("1.0"),
        )
        self.assertIsNone(target._semantic_value("not established"))

    def test_exact_requires_visible_columns_canonical_names_values_and_order(self) -> None:
        truth = complete_truth()
        first, second = target.contract.population.pair_vector()[0]
        first_record, second_record = truth[first], truth[second]
        canonical_rows = [
            (
                str(first_record["canonical_project_name"]),
                str(first_record["canonical_value"]),
            ),
            (
                str(second_record["canonical_project_name"]),
                str(second_record["canonical_value"]),
            ),
        ]
        canonical = table(0, canonical_rows)
        metric = target.evaluate_prediction(canonical, 0, truth)
        self.assertEqual(metric["exact_table_success"], 1)
        equivalent = canonical.replace("2.1", "2.1.0", 1)
        equivalent_metric = target.evaluate_prediction(equivalent, 0, truth)
        self.assertEqual(equivalent_metric["exact_table_success"], 0)
        self.assertEqual(equivalent_metric["row_f1"], 1.0)
        reversed_metric = target.evaluate_prediction(
            table(0, list(reversed(canonical_rows))), 0, truth
        )
        self.assertEqual(reversed_metric["exact_table_success"], 0)
        self.assertEqual(reversed_metric["row_f1"], 1.0)

    def test_valid_unknown_is_exact_only_with_canonical_unknown(self) -> None:
        truth = complete_truth(unknown_indices={0})
        first, second = target.contract.population.pair_vector()[0]
        rows = [
            (str(truth[first]["canonical_project_name"]), "Unknown"),
            (
                str(truth[second]["canonical_project_name"]),
                str(truth[second]["canonical_value"]),
            ),
        ]
        self.assertEqual(
            target.evaluate_prediction(table(0, rows), 0, truth)[
                "exact_table_success"
            ],
            1,
        )
        semantic = target.evaluate_prediction(
            table(0, [(rows[0][0], "unknown"), rows[1]]), 0, truth
        )
        self.assertEqual(semantic["exact_table_success"], 0)
        self.assertEqual(semantic["row_f1"], 1.0)

    def test_quality_gate_requires_strict_paired_evidence_and_negative_control(self) -> None:
        passing = metric_aggregate()
        self.assertTrue(target.quality_decision(passing)["quality_gate_passed"])
        for kind in ("wins", "loss", "sign", "soft", "truth", "ordinary"):
            changed = copy.deepcopy(passing)
            if kind == "wins":
                changed["arm_blind_paired_complete_exact"]["candidate_win"] = 5
            elif kind == "loss":
                changed["arm_blind_paired_complete_exact"]["candidate_loss"] = 1
            elif kind == "sign":
                changed["arm_blind_paired_complete_exact"][
                    "two_sided_exact_sign_test_p"
                ] = 0.0625
            elif kind == "soft":
                changed["candidate_minus_control"]["row_f1"] = -0.01
            elif kind == "truth":
                changed["truth_complete_tasks"] = 17
                changed["arm_blind_paired_complete_exact"]["task_count"] = 17
                changed["paired_complete_selection"]["selected_task_count"] = 17
            else:
                changed["ordinary_negative_control_predictions_byte_equal"] = 9
            with self.subTest(kind=kind):
                self.assertFalse(
                    target.quality_decision(changed)["quality_gate_passed"]
                )

    def test_nineteen_complete_tasks_can_pass_with_arm_blind_selection(self) -> None:
        value = metric_aggregate(complete_tasks=19)
        self.assertTrue(target.quality_decision(value)["quality_gate_passed"])
        changed = copy.deepcopy(value)
        changed["paired_complete_selection"][
            "prediction_arm_outcome_or_score_used"
        ] = True
        self.assertFalse(target.quality_decision(changed)["quality_gate_passed"])

    def test_frozen_rows_evaluate_all_forty_once_and_ordinary_equal(self) -> None:
        metrics = target.evaluate_rows(target._read_rows(), complete_truth())
        self.assertEqual(metrics["evaluation_count"], 40)
        self.assertEqual(metrics["truth_identity_count"], 40)
        self.assertEqual(metrics["truth_complete_tasks"], 20)
        self.assertEqual(metrics["arms"][target.CONTROL_ARM]["tasks"], 20)
        self.assertEqual(metrics["arms"][target.CANDIDATE_ARM]["tasks"], 20)
        self.assertEqual(
            metrics["ordinary_negative_control_predictions_byte_equal"], 10
        )

    def test_truth_snapshot_replays_unknown_and_tamper_fails(self) -> None:
        fetched = [
            {
                **spec,
                "attempt_count": 1,
                "http_status": 200,
                "transport_failure_type": None,
                "raw": pypi_payload(
                    spec["identity"], unknown=spec["index"] == 0
                ),
            }
            for spec in target.endpoint_vector()
        ]
        compressed, value = target._truth_artifact(fetched, now=1)
        self.assertEqual(value["valid_unknown_record_count"], 1)
        self.assertEqual(target.validate_truth(value, compressed), value)
        changed = bytearray(compressed)
        changed[-1] ^= 1
        with self.assertRaises(ValueError):
            target.validate_truth(value, bytes(changed))

    def test_invalid_truth_is_zero_for_both_arms_and_selection_is_arm_blind(self) -> None:
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
        metrics = target.evaluate_rows(target._read_rows(), truth["records"])
        self.assertEqual(metrics["truth_complete_tasks"], 19)
        self.assertEqual(metrics["arms"][target.CONTROL_ARM]["invalid_tasks"], 1)
        self.assertEqual(metrics["arms"][target.CANDIDATE_ARM]["invalid_tasks"], 1)
        self.assertFalse(
            metrics["paired_complete_selection"][
                "prediction_arm_outcome_or_score_used"
            ]
        )

    def test_result_is_sealed_zero_credit_and_no_benchmark_authority(self) -> None:
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
            protocol,
            truth,
            metric_aggregate(),
            now=1,
            protocol_sha256="a" * 64,
        )
        self.assertEqual(
            target.validate_result(value, expected_protocol_sha256="a" * 64),
            value,
        )
        self.assertEqual(value["positive_signed_credit_count"], 0)
        self.assertFalse(
            value["authorization"]["deepwidebench_forward_or_evaluator"]
        )

    def test_build_audit_only_authorizes_protocol_and_network_is_one_shot(self) -> None:
        tests = {
            "expected": 18,
            "observed": 18,
            "passed": True,
            "suites": [],
        }
        self.assertTrue(target._source_network_contract(ROOT / target.SOURCE))
        with (
            mock.patch.object(target, "_tests", return_value=tests),
            mock.patch.object(target, "_future_pristine", return_value=True),
            mock.patch.object(target, "_active_conflicts", return_value=[]),
            mock.patch.object(
                target.forward_control, "_lease_inactive", return_value=True
            ),
        ):
            value = target.build_audit(now=1, require_clean=False)
        self.assertEqual(target.validate_build_audit(value), value)
        self.assertTrue(
            value["authorization"]["postfreeze_quality_protocol_generation"]
        )
        self.assertFalse(
            value["authorization"]["one_truth_fetch_or_quality_evaluation"]
        )

    def test_forward_barrier_hashes_and_quality_authority_are_exact(self) -> None:
        audit, rows = target._forward_barrier()
        self.assertEqual(len(rows), 20)
        self.assertTrue(audit["authorization"]["postfreeze_quality_protocol"])
        self.assertFalse(audit["authorization"]["deepwidebench_successor_build"])
        self.assertEqual(
            target.contract.sha256(ROOT / target.contract.FORWARD_AUDIT),
            target.FORWARD_AUDIT_SHA256,
        )


if __name__ == "__main__":
    unittest.main()
