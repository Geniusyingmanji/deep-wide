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

from scripts import design_v25179_quote_aware_runtime_integration as target  # noqa: E402


class V25179QuoteAwareRuntimeIntegrationDesignTests(unittest.TestCase):
    def test_parent_clean_build_barrier_is_exact(self) -> None:
        self.assertTrue(target._parent_barrier())
        self.assertEqual(
            target.parent.base.sha256(target.PARENT_AUDIT),
            target.EXPECTED_PARENT_AUDIT_SHA256,
        )
        self.assertEqual(
            target.parent.base.sha256(target.parent.NORMALIZER_SOURCE),
            target.EXPECTED_NORMALIZER_SHA256,
        )

    def test_contract_freezes_internal_chain_and_outer_publication(self) -> None:
        value = target.integration_contract()
        self.assertTrue(
            value["internal_pipe_free_entity_table_passes_through_frozen_candidate_chain"]
        )
        self.assertTrue(value["outer_publication_runs_only_after_parent_terminal_validation"])
        self.assertTrue(
            value["final_entity_coordinates_must_be_subset_of_production_entity_coordinates"]
        )
        self.assertTrue(
            value[
                "new_or_moved_entity_causes_candidate_publication_to_fall_back_to_completed_production"
            ]
        )
        self.assertFalse(
            value["external_protocol_evaluator_deepwidebench_or_sota_authorized"]
        )

    def test_design_authorizes_implementation_build_only(self) -> None:
        value = target.build_design(now=1)
        self.assertTrue(value["design_valid"])
        self.assertEqual(value["findings"], [])
        self.assertEqual(
            value["authorization"],
            {
                "quote_aware_runtime_integration_implementation_build_only": True,
                "fresh_external_protocol_or_launch": False,
                "old_population_retry_resume_rerun_or_reuse": False,
                "binding_successor_design": False,
                "vertical_binding_policy_change": False,
                "evaluator_or_deepwidebench_or_sota": False,
            },
        )

    def test_resealed_authority_contract_credit_or_parent_tamper_fails(self) -> None:
        value = target.build_design(now=1)
        for kind in ("authority", "contract", "credit", "parent"):
            changed = copy.deepcopy(value)
            if kind == "authority":
                changed["authorization"]["fresh_external_protocol_or_launch"] = True
            elif kind == "contract":
                changed["integration_contract"][
                    "final_entity_coordinates_must_be_subset_of_production_entity_coordinates"
                ] = False
            elif kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            else:
                changed["parent_audit"]["sha256"] = "0" * 64
            changed.pop("design_payload_sha256")
            changed["design_payload_sha256"] = target.parent.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_design(changed)

    def test_design_module_is_label_blind_and_effect_free(self) -> None:
        path = ROOT / target.SOURCE
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        privileged = {
            str(node.slice.value)
            for node in ast.walk(tree)
            if isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and node.slice.value
            in {
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
        }
        self.assertEqual(privileged, set())
        self.assertNotIn("run_official_eval_local", source)
        self.assertIsNone(target.parent.base.SECRET.search(source))


if __name__ == "__main__":
    unittest.main()
