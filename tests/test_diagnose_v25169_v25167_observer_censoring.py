from __future__ import annotations

import ast
import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25167_observed_vertical_external_contract as contract  # noqa: E402
from scripts import diagnose_v25169_v25167_observer_censoring as target  # noqa: E402


class V25169ObserverCensoringDiagnosisTests(unittest.TestCase):
    def test_counts_only_censoring_funnel(self) -> None:
        value = target.build_diagnosis(now=1)
        funnel = value["content_free_funnel"]
        self.assertEqual(funnel["production_provider_output_valid_tasks"], 9)
        self.assertEqual(funnel["production_fallback_tasks"], 11)
        self.assertEqual(funnel["verified_gain_tasks"], 3)
        self.assertEqual(
            funnel["gain_by_production_validity"],
            {
                "gain_false_valid_false": 8,
                "gain_false_valid_true": 9,
                "gain_true_valid_false": 3,
                "gain_true_valid_true": 0,
            },
        )
        self.assertEqual(
            funnel["verified_gain_censored_by_invalid_production_tasks"], 3
        )
        self.assertEqual(funnel["revision_eligible_tasks"], 0)
        self.assertEqual(funnel["candidate_revision_entry_tasks"], 0)
        self.assertEqual(funnel["observer_entry_tasks"], 0)
        self.assertEqual(funnel["all_three_provider_calls_succeeded_tasks"], 20)
        self.assertFalse(any(funnel["effect_health_totals"].values()))

    def test_scanner_decodes_only_content_free_receipts_and_stage_state(self) -> None:
        line = next(
            line
            for line in (ROOT / contract.TASK_ROWS)
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        )
        value = target.safe_row(line)
        self.assertEqual(
            set(value),
            {
                "prediction_kind",
                "failures",
                "observed_receipt",
                "vertical_receipt",
                "sparse_receipt",
                "effect",
                "health",
            },
        )
        encoded = json.dumps(value, ensure_ascii=False)
        self.assertNotIn(contract.task_vector()[0]["opaque_id"], encoded)
        self.assertNotIn("https://", encoded)
        self.assertNotIn("<CLUE>", encoded)

    def test_parent_hashes_evaluator_barrier_and_authorization_are_bound(self) -> None:
        value = target.build_diagnosis(now=1)
        self.assertEqual(value["parents"]["failed_checks"], target.FAILED_CHECKS)
        self.assertTrue(all(target._absent(path) for path in target.FUTURE_SURFACES))
        self.assertFalse(value["authorization"]["binding_successor_design"])
        self.assertFalse(value["authorization"]["new_external_protocol_or_launch"])
        self.assertFalse(value["authorization"]["v25167_evaluator_or_quality_result"])
        self.assertTrue(
            value["authorization"][
                "production_normalizer_disposition_observer_build_only"
            ]
        )
        self.assertFalse(value["benchmark_status"]["sota"])

    def test_resealed_funnel_credit_or_authorization_tamper_fails(self) -> None:
        value = target.build_diagnosis(now=1)
        for kind in ("funnel", "credit", "launch", "binding"):
            changed = copy.deepcopy(value)
            if kind == "funnel":
                changed["content_free_funnel"][
                    "verified_gain_with_valid_production_tasks"
                ] = 1
            elif kind == "credit":
                changed["diagnosis"]["entropy_or_information_gain_signed_credit"] = 1
            elif kind == "launch":
                changed["authorization"]["new_external_protocol_or_launch"] = True
            else:
                changed["authorization"]["binding_successor_design"] = True
            changed.pop("diagnosis_payload_sha256")
            changed["diagnosis_payload_sha256"] = contract.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(RuntimeError):
                target.validate_diagnosis(changed)

    def test_diagnosis_source_is_label_blind_and_effect_free(self) -> None:
        path = ROOT / "scripts/diagnose_v25169_v25167_observer_censoring.py"
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        forbidden = {
            "category",
            "question_type",
            "task_category",
            "split",
            "ground_truth",
            "gold",
            "answer_key",
            "score",
            "reward",
        }
        observed = {
            str(node.slice.value)
            for node in ast.walk(tree)
            if isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and node.slice.value in forbidden
        }
        self.assertEqual(observed, set())
        calls = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        self.assertTrue(
            calls.isdisjoint(
                {
                    "complete",
                    "search_many",
                    "fetch_urls",
                    "create_connection",
                    "run_official_eval_local",
                    "Popen",
                    "run",
                }
            )
        )


if __name__ == "__main__":
    unittest.main()
