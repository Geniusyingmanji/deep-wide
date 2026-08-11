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

from deepwide_agent import v25029_evidence_conditioned_runtime as runtime  # noqa: E402
from deepwide_agent import v25030_evidence_conditioned_exact220_contract as parent  # noqa: E402
from deepwide_agent import v25056_page_self_exact220_contract as contract  # noqa: E402
from deepwide_agent.v25055_page_self_production_fetch import (  # noqa: E402
    PageSelfProductionSearchClient,
)
from scripts import control_v25056_page_self_exact220 as control  # noqa: E402
from scripts import run_v25056_page_self_exact220 as runner  # noqa: E402


def empty_fetch_receipt(*, exposed: int = 0) -> dict:
    from deepwide_agent.v24981_late_page_bound_fetch import validate_receipt
    from deepwide_agent.v24263_global_model_limiter import payload_sha256

    counts = {
        "projection_failure_count": 0,
        "input_content_characters": 8_000 if exposed else 1_000,
        "input_characters_beyond_parent_prefix": 3_000 if exposed else 0,
        "discovered_record_count": exposed,
        "admissible_record_count": exposed,
        "admissible_bound_observation_count": exposed,
        "retained_record_count": exposed,
        "retained_bound_observation_count": exposed,
        "compact_prefix_characters": 200 if exposed else 0,
        "raw_prefix_characters_retained": 4_760 if exposed else 1_000,
        "output_characters": 5_000 if exposed else 1_000,
        "positive_signed_credit_count": 0,
    }
    value = {
        "artifact_version": 1,
        "role": "v24981_content_free_late_page_fetch_receipt",
        "policy_id": "v24981_hard_deadline_late_page_bound_fetch_v1",
        "fetch_calls_snapshot": 1,
        "fetch_failures_snapshot": 0,
        "helper_result_count": 1,
        "projected_page_count": 1,
        "mechanism_engaged_page_count": exposed,
        "exact_parent_prefix_handoff_page_count": 1 - exposed,
        "candidate_evidence_changed_page_count": exposed,
        **counts,
        "maximum_network_response_bytes_per_fetch": 3_000_000,
        "parent_page_character_cap": 5_000,
        "visible_question_read_from_environment_file_or_benchmark_metadata": False,
        "question_url_title_page_record_value_prediction_answer_hash_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "additional_search_fetch_model_token_context_wall_or_network_byte_cap": False,
        "entropy_information_gain_shadow_only": True,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_receipt(value)


class PageSelfExact220Tests(unittest.TestCase):
    def test_task_vector_and_all_resource_caps_match_v25030(self) -> None:
        self.assertEqual(contract.task_vector(ROOT), parent.task_vector(ROOT))
        self.assertEqual(contract.LIMITS, parent.LIMITS)
        self.assertEqual(contract.MODEL, parent.MODEL)
        self.assertEqual(
            (contract.SELECTED_COUNT, contract.EXECUTOR_CONCURRENCY, contract.MODEL_SLOT_CAP),
            (220, 20, 8),
        )
        self.assertEqual(runtime.POLICY_ID, "v25029_single_arm_evidence_conditioned_resolve_expand_v1")

    def test_protocol_freezes_single_representation_treatment(self) -> None:
        value = contract.build_protocol(
            ROOT, now=1, tracked=False, require_clean=False, require_pristine=False
        )
        self.assertTrue(
            value["treatment_scope"][
                "sole_forward_treatment_is_v25055_page_self_fetch_projection"
            ]
        )
        self.assertEqual(
            value["mechanism_gate"]["minimum_natural_page_self_exposed_pages"], 1
        )
        self.assertFalse(value["authorization"]["single_exact220_forward"])

    def test_resealed_protocol_treatment_tamper_fails(self) -> None:
        value = contract.build_protocol(
            ROOT, now=1, tracked=False, require_clean=False, require_pristine=False
        )
        changed = copy.deepcopy(value)
        changed["treatment_scope"][
            "sole_forward_treatment_is_v25055_page_self_fetch_projection"
        ] = False
        changed.pop("protocol_payload_sha256")
        changed["protocol_payload_sha256"] = contract.payload_sha256(changed)
        with self.assertRaises(RuntimeError):
            contract.validate_protocol(ROOT, changed, tracked=False)

    def test_runner_uses_page_self_subclass_and_native_contract(self) -> None:
        runner.configure()
        self.assertIs(runner.parent.contract, contract)
        self.assertIs(
            runner.parent.RobustLatePageBoundSearchClient,
            PageSelfProductionSearchClient,
        )
        self.assertIs(runner.parent.runtime, runtime)

    def test_summary_mechanism_gate_reads_only_nested_counts(self) -> None:
        original = runner._PARENT_AGGREGATE
        runner._PARENT_AGGREGATE = lambda rows, wall: {
            "role": "parent",
            "protocol_id": contract.PROTOCOL_ID,
            "all_tasks_within_resource_caps": True,
            "summary_payload_sha256": "old",
        }
        try:
            receipt = {
                "first_wave_receipt": {"fetch_receipt": empty_fetch_receipt(exposed=1)},
                "second_wave_receipt": None,
            }
            row = {"content_free_receipt": receipt}
            original_validate = runtime.validate_receipt
            runtime.validate_receipt = lambda value: value
            try:
                value = runner._aggregate([row], 1.0)
            finally:
                runtime.validate_receipt = original_validate
        finally:
            runner._PARENT_AGGREGATE = original
        self.assertTrue(value["page_self_mechanism_gate_passed"])
        self.assertEqual(value["page_self_projection"]["mechanism_exposed_pages"], 1)
        self.assertEqual(value["page_self_projection"]["positive_signed_credit_count"], 0)

    def test_control_configuration_has_exact_test_and_auth_contract(self) -> None:
        control.configure()
        self.assertIs(control.parent.contract, contract)
        self.assertEqual(control.parent.EXPECTED_TESTS, control.EXPECTED_TESTS)
        self.assertFalse(control.PREAUDIT_AUTH["single_exact220_forward"])
        self.assertTrue(control.START_AUTH["single_exact220_forward"])

    def test_forward_closure_contains_new_seam_and_helper(self) -> None:
        closure = set(contract.forward_dependency_closure(ROOT))
        for expected in (
            contract.SOURCE,
            contract.RUNTIME,
            contract.FETCH,
            contract.FETCH_HELPER,
            contract.REPRESENTATION,
            contract.RUNNER,
        ):
            self.assertIn(expected, closure)

    def test_runner_and_contract_do_not_access_privileged_task_fields(self) -> None:
        forbidden = {
            "category", "question_type", "ground_truth", "answer_key",
            "evaluator_score", "reward",
        }
        for relative in (contract.SOURCE, contract.RUNNER, contract.CONTROL, contract.FETCH):
            tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
            accesses: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
                    if isinstance(node.slice.value, str):
                        accesses.add(node.slice.value)
                elif isinstance(node, ast.Attribute):
                    accesses.add(node.attr)
            self.assertFalse(accesses & forbidden, relative)


if __name__ == "__main__":
    unittest.main()
