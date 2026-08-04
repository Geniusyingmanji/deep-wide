from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from deepwide_agent.v24492_targeted_timed_parent import failure_projection  # noqa: E402
from scripts import v24493_total_targeted_external_gate as target  # noqa: E402
import test_v24491_proof_carrying_targeted_support as fixture  # noqa: E402


def reseal(value: dict, field: str) -> None:
    value.pop(field, None)
    value[field] = payload_sha256(value)


class V24493TotalTargetedExternalGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        fixture.V24491ProofCarryingTargetedSupportTests.setUpClass()
        owner = fixture.V24491ProofCarryingTargetedSupportTests()
        import tempfile

        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            directory = Path(temporary)
            owner.populate(directory)
            capability = owner.validate(directory)
            from deepwide_agent.v24491_proof_carrying_targeted_support import task_projection

            cls.success = task_projection(1, capability)

    @classmethod
    def tearDownClass(cls) -> None:
        fixture.V24491ProofCarryingTargetedSupportTests.tearDownClass()

    def test_invalidation_is_bound_and_population_remains_unconsumed(self) -> None:
        value = target.validate_invalidation()
        self.assertFalse(value["external_probe_launched"])
        self.assertFalse(value["same_population_consumed"])
        self.assertTrue(
            value["authorization"]["append_only_failure_aggregate_successor_design"]
        )

    def test_successor_protocol_binds_total_projection_and_is_design_only(self) -> None:
        value = target.build_protocol(now=0, require_pristine=False)
        self.assertEqual(
            value["successor_binding"]["total_projection_policy"],
            target.total.POLICY_ID,
        )
        self.assertTrue(value["successor_binding"]["same_unconsumed_population_reused"])
        self.assertFalse(value["successor_binding"]["failure_rows_claim_zero_private_effects"])
        self.assertFalse(value["authorization"]["external_probe_launch"])
        target.validate_protocol(value=value)

    def test_resealed_successor_binding_tamper_fails_closed(self) -> None:
        value = target.build_protocol(now=0, require_pristine=False)
        for field, item in (
            ("same_unconsumed_population_reused", False),
            ("failure_rows_claim_zero_private_effects", True),
            ("total_projection_policy", "other"),
        ):
            changed = copy.deepcopy(value)
            changed["successor_binding"][field] = item
            reseal(changed, "protocol_payload_sha256")
            with self.assertRaises(RuntimeError):
                target.validate_protocol(value=changed)

    def test_mechanism_gate_rejects_any_failure_as_zero_row(self) -> None:
        rows = [self.success]
        for ordinal in range(2, 9):
            row = copy.deepcopy(self.success)
            row["ordinal"] = ordinal
            rows.append(row)
        passing = target.total.aggregate_projections(rows, selected=8)
        self.assertTrue(target.mechanism_passed(passing))
        mixed = target.total.aggregate_projections(
            [*rows[:7], failure_projection(8)], selected=8
        )
        self.assertFalse(target.mechanism_passed(mixed))
        self.assertEqual(mixed["failure_as_zero_tasks"], 1)

    def test_inherited_public_result_accepts_total_schema_and_rejects_failure(self) -> None:
        rows = []
        for ordinal in range(1, 9):
            row = copy.deepcopy(self.success)
            row["ordinal"] = ordinal
            rows.append(row)
        mechanism = target.total.aggregate_projections(rows, selected=8)
        value = {
            "artifact_version": 1,
            "role": "v24492_targeted_external_result",
            "protocol_id": target.PROTOCOL_ID,
            "created_at_unix": 0,
            "selected": 8,
            "executor_count": 8,
            "model_slot_cap": 2,
            "one_wave": True,
            "batch_wall_seconds": 100.0,
            "mechanism_aggregate": mechanism,
            "observation_aggregate": {
                "selected": 8,
                "slot_timeouts_lower_bound": 0,
                "provider_deadline_failures_lower_bound": 0,
                "hosted_search_deadline_failures_lower_bound": 0,
                "hard_fetch_deadline_failures_lower_bound": 0,
                "fetch_helper_failures_lower_bound": 0,
            },
            "stage_timing_aggregate": {
                "parent_success_tasks": 8,
                "certificate_validation_invocations": 8,
                "recursive_historical_semantic_replay_tasks": 0,
                "parent_certificate_validation_wall_p95_seconds": 0.01,
            },
            "supervision_aggregate": {
                "worker_success_tasks": 8,
                "worker_hard_timeout_tasks": 0,
                "worker_nonzero_tasks": 0,
                "complete_validation_returned_tasks": 8,
                "worker_wall_max_seconds": 100.0,
            },
            "mechanism_passed": True,
            "reliability_passed": True,
            "parent_validation_passed": True,
            "latency_passed": True,
            "passed": True,
            "temporary_execution_directory_remaining": False,
            "private_task_or_web_content_persisted": False,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "official_evaluator_called": False,
            "resume_retry_skip_or_revaluation": False,
            "provenance": {"protocol_sha256": "a" * 64},
        }
        value["result_payload_sha256"] = payload_sha256(value)
        with (
            target.configured_base(),
            patch.object(
                target.base,
                "validate_observation_aggregate",
                side_effect=lambda item, **_: item,
            ),
            patch.object(
                target.base,
                "validate_stage_timing_aggregate",
                side_effect=lambda item: item,
            ),
            patch.object(
                target.base,
                "validate_supervision_aggregate",
                side_effect=lambda item: item,
            ),
        ):
            target.base.validate_public_result(value)
            changed = copy.deepcopy(value)
            changed["mechanism_aggregate"] = target.total.aggregate_projections(
                [*rows[:7], failure_projection(8)], selected=8
            )
            changed["mechanism_passed"] = False
            changed["passed"] = False
            reseal(changed, "result_payload_sha256")
            target.base.validate_public_result(changed)

    def test_configured_base_restores_all_bindings(self) -> None:
        missing = object()
        original = {
            name: getattr(target.base, name, missing) for name in target._PATCHED
        }
        with target.configured_base():
            self.assertEqual(target.base.PROTOCOL_ID, target.PROTOCOL_ID)
            self.assertIs(
                target.base.aggregate_projections,
                target.total.aggregate_projections,
            )
        for name, value in original.items():
            if value is missing:
                self.assertFalse(hasattr(target.base, name))
            else:
                self.assertIs(getattr(target.base, name), value)

    def test_runtime_source_is_label_blind(self) -> None:
        from scripts import audit_v24398_failure_observability_build as audit

        accesses, imports = audit._ast_findings(
            Path("scripts/v24493_total_targeted_external_gate.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
