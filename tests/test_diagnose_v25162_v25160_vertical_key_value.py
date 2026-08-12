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

from deepwide_agent import v25160_vertical_key_value_external_contract as contract  # noqa: E402
from scripts import diagnose_v25162_v25160_vertical_key_value as target  # noqa: E402


class V25162DiagnosisTests(unittest.TestCase):
    def test_counts_only_vertical_funnel(self) -> None:
        value = target.build_diagnosis(now=1)
        funnel = value["content_free_funnel"]
        self.assertEqual(funnel["verified_gain_tasks"], 6)
        self.assertEqual(funnel["verified_incremental_page_total"], 14)
        self.assertEqual(funnel["vertical_pipe_block_count_total"], 8)
        self.assertEqual(funnel["vertical_pipe_surface_tasks"], 2)
        self.assertEqual(funnel["vertical_identity_bound_block_count_total"], 0)
        self.assertEqual(funnel["vertical_ambiguous_page_count_total"], 0)
        for name in target.GRAMMAR_COUNTS + target.CANDIDATE_COUNTS:
            self.assertEqual(funnel[f"{name}_total"], 0)

    def test_scanner_decodes_only_two_content_free_receipts_and_booleans(self) -> None:
        line = next(
            line
            for line in (ROOT / contract.TASK_ROWS)
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        )
        value = target.safe_row(line)
        self.assertEqual(set(value), {"outer", "inner"})
        encoded = json.dumps(value, ensure_ascii=False)
        self.assertNotIn("predictions", encoded)
        self.assertNotIn(contract.task_vector()[0]["opaque_id"], encoded)
        self.assertNotIn("https://", encoded)

    def test_parent_hashes_evaluator_barrier_and_decision_are_bound(self) -> None:
        value = target.build_diagnosis(now=1)
        self.assertEqual(value["parents"]["failed_checks"], target.FAILED_CHECKS)
        self.assertTrue(all(target._absent(path) for path in target.FUTURE_SURFACES))
        self.assertFalse(value["authorization"]["v25160_evaluator_or_quality_result"])
        self.assertFalse(value["authorization"]["new_external_protocol_or_launch"])
        self.assertTrue(
            value["diagnosis"][
                "next_build_only_candidate_is_a_content_free_vertical_admission_disposition_observer"
            ]
        )
        self.assertEqual(
            value["benchmark_status"]["best_observed_single_rollout_exact_over_220"],
            9,
        )
        self.assertFalse(value["benchmark_status"]["sota"])

    def test_resealed_funnel_credit_or_authorization_tamper_fails(self) -> None:
        value = target.build_diagnosis(now=1)
        for kind in ("funnel", "credit", "launch", "policy"):
            changed = copy.deepcopy(value)
            if kind == "funnel":
                changed["content_free_funnel"][
                    "vertical_identity_bound_block_count_total"
                ] = 1
            elif kind == "credit":
                changed["diagnosis"][
                    "entropy_or_information_gain_signed_credit"
                ] = 1
            elif kind == "launch":
                changed["authorization"]["new_external_protocol_or_launch"] = True
            else:
                changed["authorization"]["vertical_binding_policy_change"] = True
            changed.pop("diagnosis_payload_sha256")
            changed["diagnosis_payload_sha256"] = contract.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(RuntimeError):
                target.validate_diagnosis(changed)

    def test_diagnosis_source_is_label_blind_and_effect_free(self) -> None:
        path = ROOT / "scripts/diagnose_v25162_v25160_vertical_key_value.py"
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
                }
            )
        )


if __name__ == "__main__":
    unittest.main()
