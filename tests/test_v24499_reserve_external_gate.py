from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from deepwide_agent.v24498_reserve_timed_parent import failure_projection  # noqa: E402
from scripts import v24499_reserve_external_gate as target  # noqa: E402
import test_v24497_proof_carrying_targeted_reserve as fixture  # noqa: E402


def reseal(value: dict, field: str) -> None:
    value.pop(field, None)
    value[field] = payload_sha256(value)


class V24499ReserveExternalGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        fixture.V24497ProofCarryingTargetedReserveTests.setUpClass()
        owner = fixture.V24497ProofCarryingTargetedReserveTests()
        import tempfile

        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            directory = Path(temporary)
            owner.populate(directory)
            capability = owner.validate(directory)
            from deepwide_agent.v24497_proof_carrying_targeted_reserve import task_projection

            cls.success = task_projection(1, capability)

    @classmethod
    def tearDownClass(cls) -> None:
        fixture.V24497ProofCarryingTargetedReserveTests.tearDownClass()

    def test_population_is_exactly_fresh_against_316_questions_and_2528_entities(self) -> None:
        self.assertTrue(target._fresh_entity_vector_valid())
        self.assertEqual(len(target._prior_questions()), 316)
        self.assertEqual(len(target.QUESTIONS), 8)
        self.assertEqual(sum(map(len, target.ENTITY_GROUPS)), 64)

    def test_protocol_is_design_only_and_contains_no_task_content(self) -> None:
        value = target.build_protocol(now=0, require_pristine=False)
        encoded = json.dumps(value, ensure_ascii=False)
        with target.configured_base():
            for ordinal in range(1, 9):
                task = target.base.neutral_task(ordinal)
                self.assertNotIn(task["opaque_id"], encoded)
                self.assertNotIn(task["question"], encoded)
        binding = value["reserve_binding"]
        self.assertEqual(binding["prior_external_question_count"], 316)
        self.assertEqual(binding["prior_external_entity_count"], 2528)
        self.assertFalse(binding["new_population_reuses_prior_question_or_entity"])
        self.assertFalse(value["authorization"]["external_probe_launch"])
        self.assertFalse(value["authorization"]["paired_dev64_or_exact220"])

    def test_resealed_protocol_tamper_fails_closed(self) -> None:
        value = target.build_protocol(now=0, require_pristine=False)
        cases = (
            lambda item: item["reserve_binding"].__setitem__(
                "new_population_reuses_prior_question_or_entity", True
            ),
            lambda item: item["reserve_binding"].__setitem__(
                "total_targeted_fetch_cap", 4
            ),
            lambda item: item["mechanism"].__setitem__(
                "reserve_additional_query_search_batch_or_model_request", True
            ),
            lambda item: item["authorization"].__setitem__(
                "external_probe_launch", True
            ),
        )
        for alter in cases:
            changed = copy.deepcopy(value)
            alter(changed)
            reseal(changed, "protocol_payload_sha256")
            with self.assertRaises(RuntimeError):
                target.validate_protocol(value=changed)

    def test_mechanism_gate_requires_complete_incremental_conversion(self) -> None:
        rows = []
        for ordinal in range(1, 9):
            row = copy.deepcopy(self.success)
            row["ordinal"] = ordinal
            rows.append(row)
        passing = target.total.aggregate_projections(rows, selected=8)
        self.assertTrue(target.mechanism_passed(passing))
        for field in (
            "reserve_engaged_tasks",
            "reserve_usable_page_tasks",
            "reserve_new_observation_tasks",
            "reserve_supporting_observation_tasks",
            "safe_change_improvement_tasks",
            "positive_decision_credit_gain_tasks",
            "total_decision_credit_gain_nats",
        ):
            changed = copy.deepcopy(passing)
            changed[field] = 0
            self.assertFalse(target.mechanism_passed(changed), field)
        mixed = target.total.aggregate_projections(
            [*rows[:7], failure_projection(8)], selected=8
        )
        self.assertFalse(target.mechanism_passed(mixed))

    def test_diagnostic_route_preserves_conversion_funnel(self) -> None:
        supervision = {"worker_hard_timeout_tasks": 0, "worker_nonzero_tasks": 0}
        cases = (
            ({"target_plan_tasks": 0}, "target_plan_coverage_successor"),
            ({"target_plan_tasks": 1, "reserve_engaged_tasks": 0}, "reserve_engagement_successor"),
            ({"target_plan_tasks": 1, "reserve_engaged_tasks": 1, "reserve_usable_page_tasks": 0}, "reserve_fetch_yield_successor"),
            ({"target_plan_tasks": 1, "reserve_engaged_tasks": 1, "reserve_usable_page_tasks": 1, "reserve_new_observation_tasks": 0}, "target_bound_projection_successor"),
            ({"target_plan_tasks": 1, "reserve_engaged_tasks": 1, "reserve_usable_page_tasks": 1, "reserve_new_observation_tasks": 1, "safe_change_improvement_tasks": 0}, "support_posterior_margin_successor"),
        )
        for mechanism, expected in cases:
            self.assertEqual(
                target.diagnostic_route(
                    mechanism,
                    supervision,
                    diagnostic=True,
                    reliability=True,
                    parent_validation=True,
                    latency=True,
                ),
                expected,
            )

    def test_configured_base_restores_all_bindings(self) -> None:
        missing = object()
        original = {
            name: getattr(target.base, name, missing)
            for name in target._CORE_PATCHED
        }
        with target.configured_base():
            self.assertEqual(target.base.PROTOCOL_ID, target.PROTOCOL_ID)
            self.assertIs(
                target.base.aggregate_projections,
                target.total.aggregate_projections,
            )
            self.assertIs(
                target.base.run_targeted_worker,
                target.run_reserve_worker,
            )
        for name, value in original.items():
            if value is missing:
                self.assertFalse(hasattr(target.base, name))
            else:
                self.assertIs(getattr(target.base, name), value)

    def test_runtime_source_is_label_blind(self) -> None:
        from scripts import audit_v24398_failure_observability_build as audit

        accesses, imports = audit._ast_findings(
            Path("scripts/v24499_reserve_external_gate.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
