from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24495_targeted_conversion_projection import (  # noqa: E402
    aggregate_projections,
    task_projection,
    validate_aggregate,
    validate_task_projection,
)
import test_v24491_proof_carrying_targeted_support as fixture  # noqa: E402


class V24495TargetedConversionProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        fixture.V24491ProofCarryingTargetedSupportTests.setUpClass()
        owner = fixture.V24491ProofCarryingTargetedSupportTests()
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            directory = Path(temporary)
            owner.populate(directory)
            cls.capability = owner.validate(directory)
        cls.projection = task_projection(1, cls.capability)

    @classmethod
    def tearDownClass(cls) -> None:
        fixture.V24491ProofCarryingTargetedSupportTests.tearDownClass()

    def test_projection_exposes_conversion_counts_without_private_content(self) -> None:
        value = self.projection
        self.assertEqual(value["targeted_cell_count"], 1)
        self.assertEqual(value["targeted_selected_source_count"], 1)
        self.assertEqual(value["targeted_usable_page_count"], 1)
        self.assertEqual(value["targeted_new_observation_count"], 1)
        self.assertTrue(value["support_selection_yield"])
        self.assertTrue(value["usable_page_yield"])
        self.assertTrue(value["new_observation_yield"])
        self.assertTrue(value["safe_change_improvement"])
        self.assertTrue(value["positive_decision_credit"])
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
        for prohibited in (
            fixture.TASK["question"], fixture.TASK["opaque_id"],
            "targeted-alpha-three.example", "| Alpha | 2025 |",
            "query_vector", "raw_content", "candidate_prediction", "sha256",
        ):
            self.assertNotIn(prohibited, encoded)

    def test_aggregate_preserves_threshold_partition_and_yields(self) -> None:
        first = copy.deepcopy(self.projection)
        second = copy.deepcopy(self.projection)
        second["ordinal"] = 2
        aggregate = aggregate_projections([first, second], selected=2)
        self.assertEqual(aggregate["target_plan_tasks"], 2)
        self.assertEqual(aggregate["support_selection_yield_tasks"], 2)
        self.assertEqual(aggregate["new_observation_yield_tasks"], 2)
        self.assertEqual(aggregate["safe_change_improvement_tasks"], 2)
        self.assertEqual(
            sum(aggregate["threshold_failure_partition_totals"].values()),
            aggregate["total_selected_target_count"],
        )
        validate_aggregate(aggregate)

    def test_raw_mapping_cannot_forge_capability(self) -> None:
        with self.assertRaises(TypeError):
            task_projection(1, self.capability.counts_only_receipts())  # type: ignore[arg-type]

    def test_projection_and_aggregate_tamper_fail_closed(self) -> None:
        for field, value in (
            ("targeted_usable_page_count", 0),
            ("support_selection_yield", False),
            ("positive_decision_credit", False),
            ("private_task_content_emitted", True),
        ):
            changed = copy.deepcopy(self.projection)
            changed[field] = value
            with self.assertRaises(ValueError):
                validate_task_projection(changed)
        aggregate = aggregate_projections([self.projection], selected=1)
        aggregate["threshold_failure_partition_totals"]["safe_change_count"] = 0
        with self.assertRaises(ValueError):
            validate_aggregate(aggregate)

    def test_coordinated_conversion_funnel_tamper_fails_closed(self) -> None:
        cases = []
        no_page = copy.deepcopy(self.projection)
        no_page["targeted_usable_page_count"] = 0
        no_page["usable_page_yield"] = False
        cases.append(no_page)
        no_observation = copy.deepcopy(self.projection)
        no_observation["targeted_new_observation_count"] = 0
        no_observation["new_observation_yield"] = False
        cases.append(no_observation)
        no_safe_change = copy.deepcopy(self.projection)
        no_safe_change["safe_change_count_after_targeted_search"] = 0
        no_safe_change["safe_change_improvement"] = False
        no_safe_change[
            "threshold_failure_partition_after_targeted_search"
        ]["safe_change_count"] = 0
        no_safe_change[
            "threshold_failure_partition_after_targeted_search"
        ]["insufficient_support_count"] = 1
        cases.append(no_safe_change)
        impossible_selection = copy.deepcopy(self.projection)
        impossible_selection["targeted_discovered_source_count"] = 0
        cases.append(impossible_selection)
        for changed in cases:
            with self.assertRaises(ValueError):
                validate_task_projection(changed)

    def test_aggregate_conversion_funnel_tamper_fails_closed(self) -> None:
        base = aggregate_projections([self.projection], selected=1)
        cases = []
        no_plan = copy.deepcopy(base)
        no_plan["target_plan_tasks"] = 0
        cases.append(no_plan)
        no_page = copy.deepcopy(base)
        no_page["usable_page_yield_tasks"] = 0
        cases.append(no_page)
        no_decision_task = copy.deepcopy(base)
        no_decision_task["positive_decision_credit_tasks"] = 0
        cases.append(no_decision_task)
        impossible_partition = copy.deepcopy(base)
        impossible_partition["threshold_failure_partition_totals"][
            "safe_change_count"
        ] = 0
        impossible_partition["threshold_failure_partition_totals"][
            "insufficient_support_count"
        ] = 1
        cases.append(impossible_partition)
        for changed in cases:
            with self.assertRaises(ValueError):
                validate_aggregate(changed)

    def test_runtime_source_is_label_blind(self) -> None:
        from scripts import audit_v24398_failure_observability_build as audit

        accesses, imports = audit._ast_findings(
            Path("src/deepwide_agent/v24495_targeted_conversion_projection.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
