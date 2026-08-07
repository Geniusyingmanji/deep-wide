from __future__ import annotations

import copy
import sys
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402
from deepwide_agent.v24804_shared_prefix_budget_ladder import run_v24804_task  # noqa: E402
from deepwide_agent.v24809_worldbank_budget_ladder_runner_integration import (  # noqa: E402
    validate_cross_artifacts as validate_old,
)
from deepwide_agent.v24812_batched_search_accounting import (  # noqa: E402
    IntegratedOutcome,
    build_envelope,
    validate_cross_artifacts,
    validate_envelope,
)
from tests.test_v24804_shared_prefix_budget_ladder import (  # noqa: E402
    Model,
    Search,
    limits,
    policy,
    task,
)


class BatchedSearch(Search):
    """Faithful batch counter: four logical queries use one provider response."""

    def search_many(self, queries, **kwargs):
        before = self.calls
        batches = super().search_many(queries, **kwargs)
        self.calls = before + 1
        return batches


def model_receipt() -> dict:
    value = {
        "artifact_version": 1,
        "role": "v24312_deadline_aware_model_receipt",
        "pool_id": "v24263_score_first_global_model_slots_v1",
        "slot_cap": 8,
        "acquisitions": 2,
        "slot_timeouts": 0,
        "provider_deadline_failures": 0,
        "total_wait_seconds": 0.0,
        "max_wait_seconds": 0.0,
        "slot_acquisition_counts": [2, 0, 0, 0, 0, 0, 0, 0],
        "cleanup_reserve_seconds": 5.0,
        "minimum_attempt_seconds": 0.05,
        "remaining_seconds_at_receipt": 100.0,
        "deadline_exhausted": False,
        "label_blind": True,
        "contains_prompt_response_question_query_url_page_prediction_answer_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return value


def transport(*, attempts: int = 1, helper_calls: int = 10) -> dict:
    return {
        "hosted_search_attempts": attempts,
        "hosted_search_deadline_failures": 0,
        "hard_fetch_helper_calls": helper_calls,
        "hard_fetch_deadline_failures": 0,
        "fetch_deadline_rejections": 10 - helper_calls,
        "fetch_helper_failures": 0,
        "deadline_exhausted": False,
    }


def result() -> dict:
    return run_v24804_task(
        task(), model=Model(), search=BatchedSearch(), limits=limits(),
        adaptive_policy=policy(), monotonic=time.monotonic,
    )


class V24812BatchedSearchAccountingTests(unittest.TestCase):
    def test_old_validator_rejects_real_batch_new_validator_accepts(self):
        value = result()
        self.assertEqual(value["receipt"]["physical_search_queries"], 4)
        self.assertEqual(value["receipt"]["search_cost"]["calls"], 1)
        with self.assertRaisesRegex(ValueError, "conservation"):
            validate_old(
                value, model_slot_receipt=model_receipt(),
                transport_health=transport(), expected_cap=8,
            )
        accounting = validate_cross_artifacts(
            value, model_slot_receipt=model_receipt(),
            transport_health=transport(), expected_cap=8,
        )
        self.assertEqual(accounting["logical_search_queries"], 4)
        self.assertEqual(accounting["provider_response_calls"], 1)
        self.assertEqual(accounting["provider_attempts"], 1)
        self.assertEqual(accounting["fetch_calls"], 10)

    def test_retry_attempt_can_exceed_provider_response_calls(self):
        accounting = validate_cross_artifacts(
            result(), model_slot_receipt=model_receipt(),
            transport_health=transport(attempts=2), expected_cap=8,
        )
        self.assertEqual(accounting["provider_response_calls"], 1)
        self.assertEqual(accounting["provider_attempts"], 2)

    def test_fetch_helper_and_deadline_rejection_partition_is_conserved(self):
        accounting = validate_cross_artifacts(
            result(), model_slot_receipt=model_receipt(),
            transport_health=transport(helper_calls=7), expected_cap=8,
        )
        self.assertEqual(accounting["hard_fetch_helper_calls"], 7)
        self.assertEqual(accounting["fetch_deadline_rejections"], 3)

    def test_impossible_counter_relations_fail_closed(self):
        value = result()
        changed = copy.deepcopy(value)
        changed["receipt"]["search_cost"]["calls"] = 3
        changed["receipt"].pop("receipt_sha256")
        from deepwide_agent.v24804_shared_prefix_budget_ladder import payload_sha256 as seal
        changed["receipt"]["receipt_sha256"] = seal(changed["receipt"])
        changed.pop("result_sha256")
        changed["result_sha256"] = seal(changed)
        with self.assertRaises(ValueError):
            validate_cross_artifacts(
                changed, model_slot_receipt=model_receipt(),
                transport_health=transport(attempts=2), expected_cap=8,
            )

    def test_envelope_binds_accounting(self):
        value = result()
        slot = model_receipt()
        health = transport(attempts=2)
        accounting = validate_cross_artifacts(
            value, model_slot_receipt=slot,
            transport_health=health, expected_cap=8,
        )
        envelope = build_envelope(IntegratedOutcome(value, slot, health, accounting))
        self.assertEqual(validate_envelope(envelope), envelope)
        changed = copy.deepcopy(envelope)
        changed["effect_accounting"]["provider_attempts"] = 99
        changed.pop("envelope_payload_sha256")
        from deepwide_agent.v24809_worldbank_budget_ladder_smoke_contract import payload_sha256 as seal
        changed["envelope_payload_sha256"] = seal(changed)
        with self.assertRaisesRegex(ValueError, "accounting"):
            validate_envelope(changed)

    def test_runtime_rejects_privileged_task_before_model_or_search_effect(self):
        from deepwide_agent.v24257_score_first_runtime import validate_visible_task

        with self.assertRaisesRegex(ValueError, "privileged"):
            validate_visible_task({**task(), "category": "hidden"})


if __name__ == "__main__":
    unittest.main()
