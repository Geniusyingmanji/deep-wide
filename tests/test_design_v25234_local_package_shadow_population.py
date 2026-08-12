from __future__ import annotations

import ast
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import (  # noqa: E402
    design_v25234_local_package_shadow_population as target,
)


class V25234LocalPackagePopulationDesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_design(now=1)

    def test_shadow_and_helper_audits_are_bound(self) -> None:
        self.assertEqual(target._parents(), target.FIXED_HASHES)

    def test_capacity_probe_is_aggregate_only_and_not_formal_selection(self) -> None:
        probe = self.value["pre_design_capacity_probe"]
        self.assertEqual(probe["counts"], target.CAPACITY_PROBE)
        self.assertTrue(probe["aggregate_only"])
        self.assertFalse(
            probe["package_identity_plaintext_or_hash_emitted_or_persisted"]
        )
        self.assertFalse(
            probe["formal_ranking_history_scan_selection_or_task_freeze_performed"]
        )

    def test_four_morphologies_are_balanced_and_removed_before_runtime(self) -> None:
        morphology = self.value["morphology_contract"]
        selection = self.value["selection_contract"]
        self.assertEqual(morphology["names"], list(target.MORPHOLOGIES))
        self.assertTrue(
            morphology["mutually_exclusive_and_exhaustive_over_admitted_population"]
        )
        self.assertTrue(morphology["morphology_removed_before_runtime_task_vector"])
        self.assertEqual(selection["tasks_per_morphology"], 16)
        self.assertEqual(selection["packages_per_task"], 4)
        self.assertEqual(selection["packages_per_morphology"], 64)
        self.assertEqual(selection["task_count"], 64)

    def test_selection_is_deterministic_history_disjoint_and_no_manual_backfill(self) -> None:
        selection = self.value["selection_contract"]
        self.assertEqual(
            selection["ranking"],
            "sha256_v25234_snapshot_morphology_package_then_package",
        )
        self.assertTrue(
            selection["first_64_ranked_history_zero_packages_per_morphology"]
        )
        self.assertTrue(
            selection["history_filter_is_predeclared_deterministic_not_manual_backfill"]
        )
        self.assertFalse(
            selection["manual_choice_reorder_replacement_or_selective_backfill"]
        )

    def test_task_and_gate_have_no_hidden_label_or_evaluator(self) -> None:
        task = self.value["task_contract"]
        gate = self.value["future_shadow_gate"]
        self.assertTrue(task["runtime_keys_exactly_opaque_id_and_question"])
        self.assertFalse(task["hidden_identity_mapping_or_morphology_field_persisted"])
        self.assertTrue(task["no_gold_answer_evaluator_quality_or_historical_prediction"])
        self.assertEqual(gate["executor_concurrency"], 32)
        self.assertEqual(gate["model_slot_cap"], 16)
        self.assertFalse(gate["evaluator_or_quality_metric"])
        self.assertFalse(
            gate["same_population_retry_resume_rerun_replacement_or_evaluation"]
        )

    def test_resealed_selection_launch_credit_or_probe_tamper_fails(self) -> None:
        for kind in ("selection", "launch", "credit", "probe"):
            changed = copy.deepcopy(self.value)
            if kind == "selection":
                changed["selection_contract"]["task_count"] = 63
            elif kind == "launch":
                changed["authorization"]["shadow_external_protocol_or_launch"] = True
            elif kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            else:
                changed["pre_design_capacity_probe"][
                    "package_identity_plaintext_or_hash_emitted_or_persisted"
                ] = True
            changed.pop("design_payload_sha256")
            changed["design_payload_sha256"] = target.base.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_design(changed)

    def test_source_has_no_privileged_runtime_field_access(self) -> None:
        tree = ast.parse((ROOT / target.SOURCE).read_text(encoding="utf-8"))
        keys = {
            node.slice.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, str)
        }
        self.assertTrue(
            keys.isdisjoint(
                {
                    "opaque_id",
                    "question",
                    "prediction",
                    "category",
                    "question_type",
                    "split",
                    "ground_truth",
                    "gold",
                    "answer_key",
                    "score",
                    "reward",
                }
            )
        )

    def test_publication_is_create_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "design.json"
            target.publish_exclusive(path, self.value)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), self.value)
            with self.assertRaises(FileExistsError):
                target.publish_exclusive(path, self.value)


if __name__ == "__main__":
    unittest.main()
