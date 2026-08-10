from __future__ import annotations

import ast
import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25035_single_column_external_contract as contract  # noqa: E402
from scripts import audit_v24635_exact220 as semantic_audit  # noqa: E402
from scripts import finalize_v25035_single_column_external as finalizer  # noqa: E402
from scripts import run_v25035_single_column_external as runner  # noqa: E402


class V25035SingleColumnExternalTests(unittest.TestCase):
    def test_population_is_fixed_fresh_bilingual_and_label_blind(self) -> None:
        tasks = contract.task_vector()
        self.assertEqual(len(tasks), 40)
        self.assertEqual(len(set(contract.PROJECTS)), 40)
        self.assertFalse(set(contract.PROJECTS) & contract.PRIOR_PROJECTS)
        self.assertEqual(len(tasks[: contract.ENGLISH_TASK_COUNT]), 20)
        self.assertEqual(len(tasks[contract.ENGLISH_TASK_COUNT :]), 20)
        self.assertTrue(all(set(row) == {"opaque_id", "question"} for row in tasks))
        self.assertTrue(
            all(contract.COLUMN_EN in row["question"] for row in tasks[:20])
        )
        self.assertTrue(
            all(contract.COLUMN_ZH in row["question"] for row in tasks[20:])
        )
        self.assertEqual(len(contract.endpoint_vector()), 40)
        self.assertTrue(
            all(url.startswith("https://pypi.org/pypi/") for url in contract.endpoint_vector())
        )

    def test_protocol_gates_require_strict_recovery_and_no_extra_effect(self) -> None:
        gates = contract.gates()
        self.assertEqual(gates["mechanism"]["fixed_denominator"], 40)
        self.assertEqual(gates["mechanism"]["minimum_candidate_natural_recoveries"], 1)
        self.assertTrue(gates["mechanism"]["candidate_fallback_strictly_less"])
        self.assertEqual(gates["mechanism"]["additional_model_search_or_fetch_calls"], 0)
        self.assertTrue(gates["quality"]["candidate_exact_strictly_greater"])
        self.assertFalse(
            contract.source_policy()[
                "public_deepwidebench_dev64_exact220_leaderboard_or_sota_authorized"
            ]
        )

    def test_readiness_is_counts_only_and_requires_all_forty(self) -> None:
        rows = [
            {
                "opaque_id": contract.task_vector()[index]["opaque_id"],
                "ready": True,
                "fetch_attempts": 1,
                "fetch_successes": 1,
                "response_bytes": 100,
            }
            for index in range(contract.TASK_COUNT)
        ]
        value = runner.validate_readiness(runner.build_readiness(rows))
        self.assertTrue(value["passed"])
        self.assertEqual(value["model_calls_before_readiness"], 0)
        self.assertNotIn("rows", value)
        rows[0]["ready"] = False
        rows[0]["fetch_successes"] = 0
        value = runner.validate_readiness(runner.build_readiness(rows))
        self.assertFalse(value["passed"])
        self.assertFalse(value["authorization"]["shared_model_forward"])

    def test_wrong_single_header_is_naturally_recovered_without_cell_rewrite(self) -> None:
        raw = "| Version |\n| --- |\n| 1.2.3rc1 |"
        control = runner._normalize_arm(
            raw,
            column=contract.COLUMN_EN,
            marker=contract.FALLBACK_EN,
            arm=contract.CONTROL_ARM,
        )
        candidate = runner._normalize_arm(
            raw,
            column=contract.COLUMN_EN,
            marker=contract.FALLBACK_EN,
            arm=contract.CANDIDATE_ARM,
        )
        self.assertEqual(control[1], "fallback")
        self.assertEqual(candidate[1], "normalized")
        self.assertIn("| 1.2.3rc1 |", candidate[0])
        self.assertEqual(candidate[3]["nonempty_factual_cell_rewrite_count"], 0)
        self.assertEqual(candidate[3]["additional_model_search_or_fetch_call_count"], 0)

    def test_exact_single_header_is_identical_between_arms(self) -> None:
        raw = (
            "```markdown\n"
            f"| {contract.COLUMN_EN} |\n"
            "| --- |\n"
            "| 2.0 |\n"
            "```"
        )
        values = [
            runner._normalize_arm(
                raw,
                column=contract.COLUMN_EN,
                marker=contract.FALLBACK_EN,
                arm=arm,
            )
            for arm in contract.ARMS
        ]
        self.assertEqual(values[0], values[1])
        self.assertEqual(values[0][1], "exact")

    def test_ambiguous_tables_fail_closed_in_both_arms(self) -> None:
        raw = "| Version |\n| --- |\n| 1.0 |\n\n| Version |\n| --- |\n| 2.0 |"
        values = [
            runner._normalize_arm(
                raw,
                column=contract.COLUMN_EN,
                marker=contract.FALLBACK_EN,
                arm=arm,
            )
            for arm in contract.ARMS
        ]
        self.assertTrue(all(value[1] == "fallback" for value in values))
        self.assertEqual(values[1][2], "ambiguous_single_column_tables")

    def _sealed_row(self, index: int, raw: str) -> dict:
        predictions = {}
        statuses = {}
        modes = {}
        audits = {}
        for arm in contract.ARMS:
            prediction, status, mode, audit = runner._normalize_arm(
                raw,
                column=contract.column_for_index(index),
                marker=contract.marker_for_index(index),
                arm=arm,
            )
            predictions[arm] = prediction
            statuses[arm] = status
            modes[arm] = mode
            audits[arm] = audit
        row = {
            "artifact_version": 1,
            "role": "v25035_single_column_external_task_result",
            "protocol_id": contract.PROTOCOL_ID,
            "index": index,
            "opaque_id": contract.task_vector()[index]["opaque_id"],
            "runtime_input_keys": ["opaque_id", "question", "same_forward_public_pypi_json"],
            "terminal": True,
            "fetch_attempts": 1,
            "fetch_successes": 1,
            "fetch_status": 200,
            "response_bytes": 100,
            "model_success": True,
            "model_usage": {
                "input_tokens": 10,
                "output_tokens": 5,
                "total_tokens": 15,
                "elapsed_milliseconds": 1,
                "provider_attempts": 1,
            },
            "raw_model_output": raw,
            "raw_model_output_sha256": __import__("hashlib").sha256(raw.encode()).hexdigest(),
            "predictions": predictions,
            "prediction_sha256": {
                arm: __import__("hashlib").sha256(predictions[arm].encode()).hexdigest()
                for arm in contract.ARMS
            },
            "normalizer_status": statuses,
            "normalizer_mode": modes,
            "normalizer_audit": audits,
            "candidate_natural_recovery": statuses[contract.CONTROL_ARM] == "fallback"
            and statuses[contract.CANDIDATE_ARM] == "normalized",
            "candidate_prediction_changed": predictions[contract.CONTROL_ARM]
            != predictions[contract.CANDIDATE_ARM],
            "candidate_data_row_count": runner._data_row_count(
                predictions[contract.CANDIDATE_ARM]
            ),
            "wall_seconds": 0.1,
            "same_raw_model_output_for_both_arms": True,
            "one_model_call_shared_by_both_arms": True,
            "additional_model_search_or_fetch_calls_from_candidate": 0,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
            "retry_resume_skip_or_population_replacement": False,
        }
        return contract.seal(row, "result_payload_sha256")

    def test_task_row_replays_both_arms_from_one_raw_output(self) -> None:
        raw = "| Version |\n| --- |\n| 3.4.5 |"
        row = runner.validate_task_row(self._sealed_row(0, raw))
        self.assertTrue(row["candidate_natural_recovery"])
        changed = copy.deepcopy(row)
        changed["predictions"][contract.CANDIDATE_ARM] = "tampered"
        changed["prediction_sha256"][contract.CANDIDATE_ARM] = __import__("hashlib").sha256(b"tampered").hexdigest()
        changed.pop("result_payload_sha256")
        changed = contract.seal(changed, "result_payload_sha256")
        with self.assertRaises(ValueError):
            runner.validate_task_row(changed)

    def test_pre_provider_model_failure_is_valid_failure_as_zero(self) -> None:
        index = 0
        predictions = {
            arm: runner._fallback(
                contract.column_for_index(index), contract.marker_for_index(index)
            )
            for arm in contract.ARMS
        }
        row = {
            "artifact_version": 1,
            "role": "v25035_single_column_external_task_result",
            "protocol_id": contract.PROTOCOL_ID,
            "index": index,
            "opaque_id": contract.task_vector()[index]["opaque_id"],
            "runtime_input_keys": ["opaque_id", "question", "same_forward_public_pypi_json"],
            "terminal": True,
            "fetch_attempts": 1,
            "fetch_successes": 1,
            "fetch_status": 200,
            "response_bytes": 100,
            "model_success": False,
            "model_usage": {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "elapsed_milliseconds": 1,
                "provider_attempts": 0,
            },
            "raw_model_output": "",
            "raw_model_output_sha256": __import__("hashlib").sha256(b"").hexdigest(),
            "predictions": predictions,
            "prediction_sha256": {
                arm: __import__("hashlib").sha256(value.encode()).hexdigest()
                for arm, value in predictions.items()
            },
            "normalizer_status": {arm: "fallback" for arm in contract.ARMS},
            "normalizer_mode": {arm: "model_failure" for arm in contract.ARMS},
            "normalizer_audit": {
                arm: {
                    "nonempty_factual_cell_rewrite_count": 0,
                    "additional_model_search_or_fetch_call_count": 0,
                    "single_column_candidate_table_count": 0,
                }
                for arm in contract.ARMS
            },
            "candidate_natural_recovery": False,
            "candidate_prediction_changed": False,
            "candidate_data_row_count": 1,
            "wall_seconds": 0.1,
            "same_raw_model_output_for_both_arms": True,
            "one_model_call_shared_by_both_arms": True,
            "additional_model_search_or_fetch_calls_from_candidate": 0,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
            "retry_resume_skip_or_population_replacement": False,
        }
        checked = runner.validate_task_row(
            contract.seal(row, "result_payload_sha256")
        )
        self.assertFalse(checked["model_success"])
        totals = runner.aggregate(
            [
                checked,
                *[
                    self._sealed_row(
                        other,
                        f"| Version |\n| --- |\n| 1.0.{other} |",
                    )
                    for other in range(1, contract.TASK_COUNT)
                ],
            ]
        )
        self.assertFalse(runner.mechanism_decision(totals)["mechanism_gate_passed"])

    def test_aggregate_and_mechanism_gate_require_natural_recovery(self) -> None:
        rows = [
            self._sealed_row(index, f"| Version |\n| --- |\n| 1.0.{index} |")
            for index in range(contract.TASK_COUNT)
        ]
        totals = runner.aggregate(rows)
        self.assertEqual(totals["candidate_natural_recoveries"], 40)
        self.assertTrue(runner.mechanism_decision(totals)["mechanism_gate_passed"])
        totals["candidate_natural_recoveries"] = 0
        totals[f"{contract.CANDIDATE_ARM}_fallback_tables"] = totals[
            f"{contract.CONTROL_ARM}_fallback_tables"
        ]
        self.assertFalse(runner.mechanism_decision(totals)["mechanism_gate_passed"])

    def test_evaluator_and_quality_gate_are_strict(self) -> None:
        prediction = (
            "```markdown\n"
            f"| {contract.COLUMN_EN} |\n"
            "| --- |\n"
            "| 1.2.3 |\n"
            "```"
        )
        value = finalizer.evaluate_prediction(
            prediction,
            column=contract.COLUMN_EN,
            gold_version="1.2.3",
            evaluator_valid=True,
        )
        self.assertTrue(value["exact_table_success"])
        bad = finalizer.evaluate_prediction(
            prediction.replace("1.2.3", "1.2.4"),
            column=contract.COLUMN_EN,
            gold_version="1.2.3",
            evaluator_valid=True,
        )
        self.assertFalse(bad["cell_correct"])
        arms = {
            contract.CONTROL_ARM: {
                "selected": 40,
                "exact_table_successes": 20,
                "cell_accuracy": 0.5,
                "schema_validity": 0.5,
                "evaluator_invalid_or_not_run": 0,
                "fallback_tasks": 20,
            },
            contract.CANDIDATE_ARM: {
                "selected": 40,
                "exact_table_successes": 21,
                "cell_accuracy": 0.525,
                "schema_validity": 0.525,
                "evaluator_invalid_or_not_run": 0,
                "fallback_tasks": 19,
            },
        }
        decision = finalizer.quality_decision(
            {"arms": arms}, {"mechanism_gate_passed": True}
        )
        self.assertTrue(decision["single_column_external_quality_gate_go"])
        arms[contract.CANDIDATE_ARM]["exact_table_successes"] = 20
        self.assertFalse(
            finalizer.quality_decision(
                {"arms": arms}, {"mechanism_gate_passed": True}
            )["single_column_external_quality_gate_go"]
        )

    def test_new_forward_sources_have_no_privileged_or_evaluator_access(self) -> None:
        for relative in (contract.SOURCE, contract.NORMALIZER, contract.RUNNER):
            path = ROOT / relative
            self.assertEqual(semantic_audit._accesses(path, ROOT), [])
            self.assertEqual(semantic_audit._evaluator_capabilities(path, ROOT), [])

    def test_contract_and_runner_do_not_import_benchmark_or_evaluator(self) -> None:
        for relative in (contract.SOURCE, contract.RUNNER):
            source = (ROOT / relative).read_text(encoding="utf-8")
            tree = ast.parse(source)
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    imports.append(node.module or "")
            self.assertFalse(
                any(
                    "deepwidebench" in name.casefold()
                    or "evaluator" in name.casefold()
                    for name in imports
                )
            )


if __name__ == "__main__":
    unittest.main()
