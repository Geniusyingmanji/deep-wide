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

from scripts import design_v25273_third_disjoint_checkpoint_population as target  # noqa: E402


class V25273ThirdDisjointCheckpointPopulationDesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_design(now=1)

    def test_fixed_parent_authority_is_exact(self) -> None:
        self.assertEqual(
            target._parents(),
            {str(path): digest for path, digest in target.FIXED_HASHES.items()},
        )

    def test_capacity_supports_exact_20_by_2_without_digit_or_backfill(self) -> None:
        probe = self.value["pre_design_capacity_probe"]
        self.assertTrue(probe["supports_fixed_20_tasks_with_2_unique_entities"])
        self.assertTrue(probe["digit_bearing_excluded_because_pair_capacity_is_one"])
        self.assertEqual(target.PACKAGES_BY_STRATUM, {"short_alpha": 20, "long_alpha": 4, "single_hyphen_alpha": 16})
        self.assertEqual(target.PACKAGE_COUNT, 40)
        self.assertEqual(target.TASK_COUNT, 20)
        self.assertFalse(probe["identity_plaintext_or_item_hash_emitted_or_persisted"])
        self.assertFalse(
            self.value["selection_contract"][
                "manual_choice_reorder_cross_stratum_fill_replacement_or_selective_backfill"
            ]
        )

    def test_history_disjointness_is_repository_scoped_and_not_overclaimed(self) -> None:
        source = self.value["source_contract"]
        self.assertTrue(
            source["selected_entity_must_have_zero_literal_history_hits_through_selection_parent"]
        )
        self.assertTrue(
            source["exact_entity_overlap_with_first_and_second_populations_must_be_zero"]
        )
        self.assertTrue(
            source[
                "repository_history_disjoint_does_not_claim_conceptual_or_unseen_benchmark_identity"
            ]
        )

    def test_paired_gate_reuses_one_live_forward_and_has_no_quality_evaluator(self) -> None:
        gate = self.value["future_paired_reliability_gate"]
        self.assertTrue(gate["one_live_provider_search_execution_per_task"])
        self.assertEqual(gate["required_clean_control_terminal"], 20)
        self.assertEqual(gate["required_injected_variants_terminal"], 60)
        self.assertTrue(gate["prediction_cost_and_effect_must_be_byte_identical_across_variants"])
        self.assertFalse(gate["additional_model_search_or_fetch_effect_for_fault_variants"])
        self.assertFalse(gate["evaluator_or_quality_metric"])

    def test_resealed_capacity_launch_credit_or_hidden_tamper_fails(self) -> None:
        for kind in ("capacity", "launch", "credit", "hidden"):
            changed = copy.deepcopy(self.value)
            if kind == "capacity":
                changed["pre_design_capacity_probe"]["counts"]["history_zero_total"] -= 1
            elif kind == "launch":
                changed["authorization"]["fresh_external_protocol_or_launch"] = True
            elif kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            else:
                changed["task_contract"]["hidden_stratum"] = True
            changed.pop("design_payload_sha256")
            changed["design_payload_sha256"] = target.contract.payload_sha256(changed)
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
