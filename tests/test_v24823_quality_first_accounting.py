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

from deepwide_agent.v24804_shared_prefix_budget_ladder import (  # noqa: E402
    payload_sha256,
)
from deepwide_agent.v24819_quality_first_controller import (  # noqa: E402
    QualityFirstPolicy,
    run_v24819_task,
)
from deepwide_agent.v24823_quality_first_accounting import (  # noqa: E402
    IntegratedOutcome,
    build_envelope,
    validate_cross_artifacts,
    validate_envelope,
)
from tests.test_v24804_shared_prefix_budget_ladder import (  # noqa: E402
    Model,
    Search,
    limits,
    task,
)
from tests.test_v24812_batched_search_accounting import (  # noqa: E402
    BatchedSearch,
    model_receipt,
    transport,
)


def result():
    return run_v24819_task(
        task(),
        model=Model(),
        search=BatchedSearch(),
        limits=limits(),
        quality_first_policy=QualityFirstPolicy(),
        monotonic=time.monotonic,
    )


class V24823QualityFirstAccountingTests(unittest.TestCase):
    def test_quality_first_result_conserves_effects(self) -> None:
        accounting = validate_cross_artifacts(
            result(),
            model_slot_receipt=model_receipt(),
            transport_health=transport(),
            expected_cap=8,
        )
        self.assertEqual(accounting["logical_model_calls"], 2)
        self.assertEqual(accounting["logical_search_queries"], 4)
        self.assertEqual(accounting["provider_response_calls"], 1)
        self.assertEqual(accounting["logical_fetch_targets"], 10)
        self.assertTrue(
            accounting["mandatory_required_coverage_precedes_cost_stopping"]
        )
        self.assertTrue(accounting["entropy_shadow_only_not_signed_credit"])

    def test_provider_attempts_can_exceed_response_calls(self) -> None:
        accounting = validate_cross_artifacts(
            result(),
            model_slot_receipt=model_receipt(),
            transport_health=transport(attempts=2),
            expected_cap=8,
        )
        self.assertEqual(accounting["provider_response_calls"], 1)
        self.assertEqual(accounting["provider_attempts"], 2)

    def test_impossible_effect_relation_is_rejected(self) -> None:
        health = transport(attempts=1)
        health["hard_fetch_helper_calls"] = 9
        health["fetch_deadline_rejections"] = 0
        with self.assertRaisesRegex(ValueError, "conservation"):
            validate_cross_artifacts(
                result(),
                model_slot_receipt=model_receipt(),
                transport_health=health,
                expected_cap=8,
            )

    def test_envelope_binds_result_and_accounting(self) -> None:
        value = result()
        slot = model_receipt()
        health = transport(attempts=2)
        accounting = validate_cross_artifacts(
            value,
            model_slot_receipt=slot,
            transport_health=health,
            expected_cap=8,
        )
        envelope = build_envelope(
            IntegratedOutcome(value, slot, health, accounting)
        )
        self.assertEqual(validate_envelope(envelope), envelope)
        changed = copy.deepcopy(envelope)
        changed["effect_accounting"]["provider_attempts"] = 99
        changed.pop("envelope_payload_sha256")
        changed["envelope_payload_sha256"] = payload_sha256(changed)
        with self.assertRaisesRegex(ValueError, "accounting"):
            validate_envelope(changed)

    def test_privileged_task_is_rejected_before_effect(self) -> None:
        model = Model()
        search = Search()
        with self.assertRaisesRegex(ValueError, "privileged"):
            run_v24819_task(
                {**task(), "category": "hidden"},
                model=model,
                search=search,
                limits=limits(),
                quality_first_policy=QualityFirstPolicy(),
            )
        self.assertEqual(model.requests, 0)
        self.assertEqual(search.calls, 0)


if __name__ == "__main__":
    unittest.main()
