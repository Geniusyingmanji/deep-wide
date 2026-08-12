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

from scripts import design_v25239_source_package_shadow_population as target  # noqa: E402


class V25239SourcePackagePopulationDesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_design(now=1)

    def test_failure_and_shadow_authority_are_bound(self) -> None:
        self.assertEqual(target._parents(), target.FIXED_HASHES)

    def test_capacity_counts_are_conserved_mutually_exclusive_and_sufficient(self) -> None:
        counts = self.value["pre_design_capacity_probe"]["counts"]
        self.assertEqual(counts, target.CAPACITY_PROBE)
        self.assertEqual(
            sum(counts[name] for name in (*target.STRATA, "excluded_other")),
            counts["source_name_disjoint_from_all_installed_binary_names"],
        )
        self.assertTrue(all(counts[name] >= 64 for name in target.STRATA))
        self.assertFalse(
            self.value["pre_design_capacity_probe"][
                "identity_plaintext_or_item_hash_emitted_or_persisted"
            ]
        )

    def test_source_entities_are_binary_disjoint_and_network_free(self) -> None:
        source = self.value["source_contract"]
        self.assertTrue(source["admitted_source_name_must_not_equal_any_installed_binary_name"])
        self.assertTrue(source["entity_disjoint_from_v25235_binary_population_by_construction"])
        self.assertFalse(source["network_or_external_snapshot_endpoint"])

    def test_selection_repairs_deadline_and_records_all_subprocess_failures(self) -> None:
        selection = self.value["selection_contract"]
        self.assertEqual(selection["history_scan_worker_cap"], 16)
        self.assertEqual(selection["whole_selection_wall_ceiling_seconds"], 240)
        self.assertTrue(selection["all_admitted_candidates_checked_once_with_bounded_concurrency"])
        self.assertTrue(selection["subprocess_returncode_timeout_and_stderr_are_terminal_receipt_fields"])
        self.assertFalse(selection["v25237_command_population_or_rank_salt_reused"])

    def test_runtime_boundary_and_gate_are_label_blind(self) -> None:
        task = self.value["task_contract"]
        gate = self.value["future_shadow_gate"]
        self.assertTrue(task["runtime_keys_exactly_opaque_id_and_question"])
        self.assertFalse(task["hidden_identity_mapping_or_stratum_field_persisted"])
        self.assertEqual(gate["executor_concurrency"], 32)
        self.assertEqual(gate["model_slot_cap"], 16)
        self.assertFalse(gate["evaluator_or_quality_metric"])

    def test_resealed_capacity_launch_retry_credit_or_hidden_tamper_fails(self) -> None:
        for kind in ("capacity", "launch", "retry", "credit", "source_hidden", "selection_hidden", "gate_hidden"):
            changed = copy.deepcopy(self.value)
            if kind == "capacity":
                changed["pre_design_capacity_probe"]["counts"]["short_alpha"] -= 1
            elif kind == "launch":
                changed["authorization"]["shadow_external_protocol_or_launch"] = True
            elif kind == "retry":
                changed["selection_contract"]["v25237_command_population_or_rank_salt_reused"] = True
            elif kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            elif kind == "source_hidden":
                changed["source_contract"]["hidden_authority"] = True
            elif kind == "selection_hidden":
                changed["selection_contract"]["hidden_authority"] = True
            else:
                changed["future_shadow_gate"]["hidden_authority"] = True
            changed.pop("design_payload_sha256")
            changed["design_payload_sha256"] = target.base.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_design(changed)

    def test_source_has_no_privileged_runtime_field_access(self) -> None:
        tree = ast.parse((ROOT / target.SOURCE).read_text(encoding="utf-8"))
        privileged = {
            node.slice.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and node.slice.value in {
                "category", "question_type", "task_category", "split",
                "ground_truth", "gold", "answer_key", "score", "reward",
            }
        }
        self.assertEqual(privileged, set())

    def test_publication_is_create_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "design.json"
            target.publish_exclusive(path, self.value)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), self.value)
            with self.assertRaises(FileExistsError):
                target.publish_exclusive(path, self.value)


if __name__ == "__main__":
    unittest.main()
