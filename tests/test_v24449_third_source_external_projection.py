from __future__ import annotations

import copy
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24447_third_source_entropy_to_decision import (  # noqa: E402
    build_envelope,
    run_v24447_task,
)
from deepwide_agent.v24448_serialized_third_source_envelope import (  # noqa: E402
    validate_serialized_envelope,
    validate_serialized_observed_bundle,
)
from scripts import v24449_third_source_external_projection as target  # noqa: E402
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import SEED, TASK  # noqa: E402
from test_v24412_receipt_snapshot_diagnosis import AdvancingClock  # noqa: E402
from test_v24447_third_source_entropy_to_decision import clients  # noqa: E402


GATES = {
    "selected": 16,
    "executor_count": 8,
    "model_slot_cap": 2,
    "maximum_batch_wall_seconds": 480.0,
    "maximum_slot_timeouts": 0,
    "maximum_provider_deadline_failures": 0,
    "maximum_hosted_search_deadline_failures": 0,
    "maximum_hard_fetch_deadline_failures": 5,
    "maximum_fetch_helper_failures": 5,
    "maximum_deadline_exhausted_tasks": 0,
    "minimum_full_proposal_partition_tasks": 0,
    "minimum_two_active_source_tasks": 0,
    "minimum_active_page_tasks": 0,
    "minimum_combined_observation_tasks": 0,
    "minimum_novel_structured_observation_tasks": 0,
    "minimum_positive_epistemic_tasks": 0,
    "minimum_safe_change_tasks": 0,
    "minimum_epistemic_credit_nats": 0.0,
    "minimum_title_novel_observation_tasks": 0,
    "minimum_title_positive_epistemic_tasks": 0,
    "minimum_title_safe_change_tasks": 0,
    "minimum_title_decision_credit_nats": 0.0,
    "minimum_narrative_novel_observation_tasks": 0,
    "minimum_narrative_positive_epistemic_tasks": 0,
    "minimum_narrative_safe_change_tasks": 0,
    "minimum_narrative_decision_credit_nats": 0.0,
    "minimum_third_source_safe_change_tasks": 1,
    "minimum_third_source_decision_credit_nats": 1e-12,
}


class V24449ThirdSourceExternalProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        clock = AdvancingClock()
        model, search = clients(Path(cls.temporary.name), clock, third=True)
        outcome = run_v24447_task(
            TASK,
            model=model,
            search=search,
            partition_seed_sha256=SEED,
            limits=limits(),
            monotonic=clock,
        )
        cls.envelope = build_envelope(outcome)
        wire = json.loads(
            json.dumps(cls.envelope, ensure_ascii=False, sort_keys=True)
        )
        cls.unobserved_capability = validate_serialized_envelope(wire)
        cls.capability = validate_serialized_observed_bundle(
            wire,
            model_slot_receipt=outcome.model_slot_receipt,
            transport_health=outcome.transport_health,
            search_single_shot_receipt=outcome.search_single_shot_receipt,
            expected_cap=2,
        )
        cls.value = target.task_projection(1, cls.capability)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_projection_converts_entropy_to_decision_without_private_content(self) -> None:
        value = self.value
        self.assertTrue(value["passed"])
        self.assertEqual(value["third_source_candidate_count"], 1)
        self.assertEqual(value["third_source_additional_fetch_effects"], 1)
        self.assertEqual(value["third_source_safe_change_count"], 1)
        self.assertGreater(value["third_source_decision_credit_total_nats"], 0)
        self.assertEqual(value["third_source_additional_model_requests"], 0)
        self.assertEqual(value["third_source_additional_logical_queries"], 0)
        self.assertEqual(value["third_source_additional_search_batches"], 0)
        self.assertTrue(value["third_source_complete_envelope_validated_once"])
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
        for private in ("Alpha", "Beta", "2025", "https://"):
            self.assertNotIn(private, encoded)
        self.assertIsNone(re.search(r"task_[0-9a-f]{24}", encoded))

    def test_raw_or_forged_mapping_is_rejected(self) -> None:
        with self.assertRaises(TypeError):
            target.task_projection(1, self.envelope)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            target.task_projection(1, self.unobserved_capability)

    def test_partition_credit_or_effect_tamper_fails(self) -> None:
        for name in (
            "third_source_insufficient_support_count",
            "third_source_decision_credit_total_nats",
            "third_source_additional_fetch_effects",
            "third_source_complete_envelope_validated_once",
        ):
            with self.subTest(name=name):
                altered = copy.deepcopy(self.value)
                if isinstance(altered[name], bool):
                    altered[name] = not altered[name]
                else:
                    altered[name] += 1
                with self.assertRaises(RuntimeError):
                    target.validate_task_projection(altered)

    def test_aggregate_preserves_partition_and_requires_decision_credit(self) -> None:
        tasks = []
        for ordinal in range(1, 17):
            item = copy.deepcopy(self.value)
            item["ordinal"] = ordinal
            item["checks"] = target.task_checks(item)
            item["passed"] = all(item["checks"].values())
            target.validate_task_projection(item)
            tasks.append(item)
        summary = target.aggregate_tasks(tasks, GATES)
        target.validate_aggregate(summary, GATES)
        self.assertTrue(summary["passed"])
        self.assertEqual(summary["third_source_safe_change_tasks"], 16)
        self.assertEqual(summary["third_source_total_safe_change_count"], 16)
        self.assertEqual(summary["third_source_total_additional_fetch_effects"], 16)
        self.assertEqual(summary["third_source_validated_once_tasks"], 16)

    def test_failure_as_zero_does_not_claim_single_validation(self) -> None:
        tasks = []
        for ordinal in range(1, 17):
            item = copy.deepcopy(self.value)
            item["ordinal"] = ordinal
            item["checks"] = target.task_checks(item)
            item["passed"] = all(item["checks"].values())
            tasks.append(item)
        tasks[0] = target.local_failure(1)
        summary = target.aggregate_tasks(tasks, GATES)
        self.assertFalse(summary["passed"])
        self.assertEqual(summary["third_source_validated_once_tasks"], 15)
        self.assertFalse(summary["all_third_source_envelopes_validated_once"])


if __name__ == "__main__":
    unittest.main()
