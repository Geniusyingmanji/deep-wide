from __future__ import annotations

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

from scripts import design_v25255_disjoint_observed_reliability_population as target  # noqa: E402


class V25255DisjointObservedReliabilityPopulationDesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_design(now=1)

    def test_fixed_parent_authority_is_exact(self) -> None:
        self.assertEqual(
            target._parents(),
            {str(path): digest for path, digest in target.FIXED_HASHES.items()},
        )

    def test_capacity_supports_64_by_2_but_not_64_by_3(self) -> None:
        probe = self.value["pre_design_capacity_probe"]
        self.assertFalse(probe["supports_64_tasks_with_3_unique_entities"])
        self.assertTrue(probe["supports_64_tasks_with_2_unique_entities"])
        self.assertEqual(sum(target.PACKAGES_BY_STRATUM.values()), 128)
        self.assertEqual(sum(target.TASKS_BY_STRATUM.values()), 64)
        self.assertFalse(probe["identity_plaintext_or_item_hash_emitted_or_persisted"])

    def test_old_population_entity_disjointness_is_required(self) -> None:
        source = self.value["source_contract"]
        self.assertTrue(source["selected_source_name_must_not_appear_in_v25240_visible_questions"])
        self.assertTrue(source["entity_disjoint_from_v25240_by_exact_visible_identity"])
        self.assertFalse(source["network_or_external_snapshot_endpoint"])

    def test_reliability_gate_uses_truthful_caps_and_no_header_gate(self) -> None:
        gate = self.value["future_reliability_gate"]
        self.assertEqual((gate["physical_query_cap_per_task"], gate["physical_fetch_cap_per_task"], gate["physical_model_forward_cap_per_task"]), (4, 14, 4))
        self.assertEqual(gate["required_runtime_completed_tasks"], 64)
        self.assertTrue(gate["header_totality_entry_or_candidate_gate_removed"])
        self.assertFalse(gate["evaluator_or_quality_metric"])

    def test_task_boundary_is_visible_only(self) -> None:
        task = self.value["task_contract"]
        self.assertTrue(task["runtime_keys_exactly_opaque_id_and_question"])
        self.assertFalse(task["hidden_identity_mapping_or_stratum_field_persisted"])
        self.assertTrue(task["each_question_lists_exactly_two_packages_in_frozen_order"])

    def test_resealed_capacity_launch_credit_or_hidden_tamper_fails(self) -> None:
        for kind in ("capacity", "launch", "credit", "hidden"):
            changed = copy.deepcopy(self.value)
            if kind == "capacity":
                changed["pre_design_capacity_probe"]["counts"]["remaining_history_zero_total"] -= 1
            elif kind == "launch":
                changed["authorization"]["fresh_external_protocol_or_launch"] = True
            elif kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            else:
                changed["selection_contract"]["hidden_authority"] = True
            changed.pop("design_payload_sha256")
            changed["design_payload_sha256"] = target.base.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_design(changed)

    def test_publication_is_create_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "design.json"
            target.publish_exclusive(path, self.value)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), self.value)
            with self.assertRaises(FileExistsError):
                target.publish_exclusive(path, self.value)


if __name__ == "__main__":
    unittest.main()
