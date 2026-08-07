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

from deepwide_agent.v24804_shared_prefix_budget_ladder import payload_sha256  # noqa: E402
from deepwide_agent.v24819_quality_first_controller import (  # noqa: E402
    QualityFirstPolicy,
    run_v24819_task,
)
from deepwide_agent.v24826_worldbank_exact_api_transport import (  # noqa: E402
    POLICY_ID as EXACT_POLICY_ID,
    RECEIPT_ROLE,
)
from deepwide_agent.v24828_dedicated_exact_accounting import (  # noqa: E402
    IntegratedOutcome,
    build_envelope,
    run_v24828_task,
    validate_cross_artifacts,
    validate_effect_accounting,
    validate_envelope,
)
from tests.test_v24804_shared_prefix_budget_ladder import (  # noqa: E402
    Model,
    limits,
    task,
)
from tests.test_v24812_batched_search_accounting import (  # noqa: E402
    BatchedSearch,
    model_receipt,
)


def result() -> dict:
    return run_v24819_task(
        task(),
        model=Model(),
        search=BatchedSearch(),
        limits=limits(),
        quality_first_policy=QualityFirstPolicy(),
        monotonic=time.monotonic,
    )


def exact_receipt(*, successes: int = 8, exhausted: int = 0) -> dict:
    value = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": EXACT_POLICY_ID,
        "allowed_target_count": 8,
        "logical_requests": 8,
        "direct_helper_calls": 8,
        "direct_deadline_rejections": 0,
        "helper_total_wall_timeouts": 0,
        "helper_nonzero_exits": 0,
        "helper_invalid_results": 0,
        "terminal_successes": successes,
        "terminal_exhausted": exhausted,
        "provider_attempts": 8,
        "provider_retries": 0,
        "response_bytes": 100 * successes,
        "http_status_counts": {"200": successes},
        "attempt_failure_class_counts": {"http_404": exhausted} if exhausted else {},
        "sequential_within_task": True,
        "redirects_allowed": False,
        "unbound_exact_url_network_effect_allowed": False,
        "question_country_url_page_value_prediction_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return value


def generic_transport(*, attempts: int = 1, helper_calls: int = 2) -> dict:
    return {
        "hosted_search_attempts": attempts,
        "hosted_search_deadline_failures": 0,
        "hard_fetch_helper_calls": helper_calls,
        "hard_fetch_deadline_failures": 0,
        "fetch_deadline_rejections": 0,
        "fetch_helper_failures": 0,
        "deadline_exhausted": False,
    }


class V24828DedicatedExactAccountingTests(unittest.TestCase):
    def test_two_plus_eight_conserves_fixed_ten_fetch_budget(self) -> None:
        accounting = validate_cross_artifacts(
            result(),
            model_slot_receipt=model_receipt(),
            generic_transport_health=generic_transport(),
            exact_transport_receipt=exact_receipt(),
            expected_cap=8,
        )
        self.assertEqual(accounting["logical_fetch_targets"], 10)
        self.assertEqual(accounting["generic_fetch_targets"], 2)
        self.assertEqual(accounting["dedicated_exact_fetch_targets"], 8)
        self.assertTrue(accounting["combined_fetch_budget_conserved"])

    def test_exact_provider_retries_are_separate_from_search_provider(self) -> None:
        exact = exact_receipt()
        exact["provider_attempts"] = 10
        exact["provider_retries"] = 2
        exact["attempt_failure_class_counts"] = {"timeout": 2}
        exact.pop("receipt_payload_sha256")
        exact["receipt_payload_sha256"] = payload_sha256(exact)
        accounting = validate_cross_artifacts(
            result(),
            model_slot_receipt=model_receipt(),
            generic_transport_health=generic_transport(attempts=2),
            exact_transport_receipt=exact,
            expected_cap=8,
        )
        self.assertEqual(accounting["provider_attempts"], 2)
        self.assertEqual(accounting["exact_provider_attempts"], 10)

    def test_old_ten_generic_helper_assumption_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "cross-transport"):
            validate_cross_artifacts(
                result(),
                model_slot_receipt=model_receipt(),
                generic_transport_health=generic_transport(helper_calls=10),
                exact_transport_receipt=exact_receipt(),
                expected_cap=8,
            )

    def test_resealed_exact_count_tamper_fails_closed(self) -> None:
        exact = exact_receipt()
        exact["logical_requests"] = 7
        exact["direct_helper_calls"] = 7
        exact["terminal_successes"] = 7
        exact["provider_attempts"] = 7
        exact["response_bytes"] = 700
        exact["http_status_counts"] = {"200": 7}
        exact.pop("receipt_payload_sha256")
        exact["receipt_payload_sha256"] = payload_sha256(exact)
        with self.assertRaises(ValueError):
            validate_cross_artifacts(
                result(),
                model_slot_receipt=model_receipt(),
                generic_transport_health=generic_transport(),
                exact_transport_receipt=exact,
                expected_cap=8,
            )

    def test_exhausted_exact_target_is_conserved_without_quality_claim(self) -> None:
        accounting = validate_cross_artifacts(
            result(),
            model_slot_receipt=model_receipt(),
            generic_transport_health=generic_transport(),
            exact_transport_receipt=exact_receipt(successes=7, exhausted=1),
            expected_cap=8,
        )
        self.assertEqual(accounting["exact_terminal_successes"], 7)
        self.assertEqual(accounting["exact_terminal_exhausted"], 1)
        self.assertTrue(accounting["entropy_shadow_only_not_signed_credit"])

    def test_envelope_binds_both_transport_receipts(self) -> None:
        value = result()
        slot = model_receipt()
        generic = generic_transport(attempts=2)
        exact = exact_receipt()
        accounting = validate_cross_artifacts(
            value,
            model_slot_receipt=slot,
            generic_transport_health=generic,
            exact_transport_receipt=exact,
            expected_cap=8,
        )
        envelope = build_envelope(
            IntegratedOutcome(value, slot, generic, exact, accounting)
        )
        self.assertEqual(validate_envelope(envelope), envelope)
        changed = copy.deepcopy(envelope)
        changed["effect_accounting"]["generic_fetch_targets"] = 3
        changed["effect_accounting"].pop("accounting_payload_sha256")
        changed["effect_accounting"]["accounting_payload_sha256"] = payload_sha256(
            changed["effect_accounting"]
        )
        changed.pop("envelope_payload_sha256")
        changed["envelope_payload_sha256"] = payload_sha256(changed)
        with self.assertRaises(ValueError):
            validate_envelope(changed)

    def test_privileged_input_rejected_before_transport_type_checks(self) -> None:
        with self.assertRaisesRegex(ValueError, "privileged"):
            run_v24828_task(
                {**task(), "category": "hidden"},
                model=object(),
                search=object(),
                limits=limits(),
                quality_first_policy=QualityFirstPolicy(),
                monotonic=time.monotonic,
            )


if __name__ == "__main__":
    unittest.main()
