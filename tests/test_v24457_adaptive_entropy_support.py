from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256  # noqa: E402
from deepwide_agent.v24438_bounded_narrative_effect_runner import (  # noqa: E402
    MAXIMUM_PROVIDER_EFFECT_SECONDS,
)
from deepwide_agent.v24457_adaptive_entropy_support import (  # noqa: E402
    MAXIMUM_ADDITIONAL_FETCHES,
    MAXIMUM_TOTAL_FETCHES,
    build_envelope,
    run_v24457_task,
    validate_envelope,
    validate_result,
    validate_step_receipt,
)
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import SEED, TASK  # noqa: E402
from test_v24412_receipt_snapshot_diagnosis import AdvancingClock  # noqa: E402
from test_v24447_third_source_entropy_to_decision import (  # noqa: E402
    KNOWN_BASELINE,
    ThreeSourceNarrativeSearch,
    clients as parent_clients,
)


class AdaptiveLeadSearch(ThreeSourceNarrativeSearch):
    def __init__(self, *args, mode: str, **kwargs):
        super().__init__(*args, **kwargs)
        self.mode = mode
        self.adaptive_single_fetches = 0

    def _request(self, queries):  # type: ignore[override]
        payload = super()._request(queries)
        if self.request_invocations == 3:
            sources = payload["output"][0]["action"]["sources"]
            sources.extend(
                [
                    {
                        "type": "web_source",
                        "url": "https://active-alpha-four.example/record",
                        "title": "Alpha official founding chronology",
                    },
                    {
                        "type": "web_source",
                        "url": "https://active-alpha-five.example/record",
                        "title": "Alpha historical founding archive",
                    },
                ]
            )
        return payload

    def fetch_urls(self, requests_):
        requested = list(requests_)
        batches = super().fetch_urls(requested)
        # The parent consumes invocations 1--3.  Adaptive source steps are
        # invocations 4--6, one source each.
        if self.mode in {"delayed_safe", "unreachable"} and self.fetch_invocations == 3:
            for batch in batches:
                for result in batch["results"]:
                    result["raw_content"] = (
                        "The product publishes documentation and software."
                    )
        elif self.fetch_invocations >= 4 and len(requested) == 1:
            self.adaptive_single_fetches += 1
            for batch in batches:
                for result in batch["results"]:
                    if self.mode == "delayed_safe":
                        result["raw_content"] = (
                            "Alpha was founded in 2025 and later expanded."
                        )
                    elif self.mode == "unreachable":
                        result["raw_content"] = (
                            "The product publishes documentation and software."
                        )
                    else:
                        raise AssertionError(self.mode)
        return batches


def clients(output: Path, clock: AdvancingClock, *, mode: str):
    model, old_search = parent_clients(output, clock, third=False)
    model.inner.timeout = MAXIMUM_PROVIDER_EFFECT_SECONDS
    model.inner.baseline = KNOWN_BASELINE
    search = AdaptiveLeadSearch(clock, deadline=300, mode=mode)
    search.timeout = MAXIMUM_PROVIDER_EFFECT_SECONDS
    search.static_search_timeout_seconds = MAXIMUM_PROVIDER_EFFECT_SECONDS
    del old_search
    return model, search


class V24457AdaptiveEntropySupportTests(unittest.TestCase):
    def run_case(self, mode: str):
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        self.addCleanup(temporary.cleanup)
        clock = AdvancingClock()
        model, search = clients(Path(temporary.name), clock, mode=mode)
        outcome = run_v24457_task(
            TASK,
            model=model,
            search=search,
            partition_seed_sha256=SEED,
            limits=limits(),
            monotonic=clock,
        )
        validate_result(outcome.adaptive_result)
        validate_envelope(build_envelope(outcome))
        return outcome, model, search

    def test_first_supporting_source_stops_immediately_on_safe_decision(self) -> None:
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        self.addCleanup(temporary.cleanup)
        clock = AdvancingClock()
        model, search = parent_clients(Path(temporary.name), clock, third=True)
        outcome = run_v24457_task(
            TASK,
            model=model,
            search=search,
            partition_seed_sha256=SEED,
            limits=limits(),
            monotonic=clock,
        )
        receipt = outcome.adaptive_result["adaptive_support_receipt"]
        self.assertEqual(receipt["adaptive_fetch_attempt_count"], 1)
        self.assertEqual(receipt["stop_reason"], "safe_decision")
        self.assertEqual(receipt["safe_change_count"], 1)
        self.assertGreater(receipt["final_decision_credit_total_nats"], 0)

    def test_third_additional_source_can_cross_unchanged_gate(self) -> None:
        outcome, model, search = self.run_case("delayed_safe")
        receipt = outcome.adaptive_result["adaptive_support_receipt"]
        steps = outcome.adaptive_result["adaptive_private_state"][
            "adaptive_step_receipts"
        ]
        self.assertEqual(receipt["adaptive_fetch_attempt_count"], 3)
        self.assertEqual(receipt["adaptive_usable_page_count"], 3)
        self.assertEqual(receipt["stop_reason"], "safe_decision")
        self.assertEqual(receipt["safe_change_count"], 1)
        self.assertGreater(receipt["final_decision_credit_total_nats"], 0)
        self.assertEqual([item["step_ordinal"] for item in steps], [1, 2, 3])
        self.assertEqual(steps[-1]["stop_reason_after_step"], "safe_decision")
        self.assertEqual(model.acquisitions, 2)
        self.assertEqual(search.request_invocations, 3)
        self.assertEqual(search.fetch_invocations, 6)
        self.assertEqual(receipt["total_fetch_cap"], MAXIMUM_TOTAL_FETCHES)

    def test_uninformative_steps_stop_when_support_is_unreachable(self) -> None:
        outcome, _, search = self.run_case("unreachable")
        receipt = outcome.adaptive_result["adaptive_support_receipt"]
        steps = outcome.adaptive_result["adaptive_private_state"][
            "adaptive_step_receipts"
        ]
        self.assertLess(receipt["adaptive_fetch_attempt_count"], MAXIMUM_ADDITIONAL_FETCHES)
        self.assertEqual(receipt["stop_reason"], "support_unreachable")
        self.assertEqual(receipt["safe_change_count"], 0)
        self.assertEqual(receipt["final_decision_credit_total_nats"], 0)
        self.assertEqual(steps[-1]["stop_reason_after_step"], "support_unreachable")
        self.assertEqual(search.request_invocations, 3)

    def test_step_receipt_entropy_credit_and_stop_tamper_fail_closed(self) -> None:
        outcome, _, _ = self.run_case("delayed_safe")
        step = outcome.adaptive_result["adaptive_private_state"][
            "adaptive_step_receipts"
        ][1]
        for field in (
            "positive_acquisition_credit_nats",
            "post_minimum_support_deficit",
            "stop_reason_after_step",
        ):
            with self.subTest(field=field):
                altered = copy.deepcopy(step)
                if field == "stop_reason_after_step":
                    altered[field] = "safe_decision"
                else:
                    altered[field] += 1
                with self.assertRaises(ValueError):
                    validate_step_receipt(altered)

    def test_lead_order_threshold_or_effect_tamper_fails_closed(self) -> None:
        outcome, _, _ = self.run_case("delayed_safe")
        envelope = build_envelope(outcome)
        for field in ("lead_order", "threshold", "effect"):
            with self.subTest(field=field):
                altered = copy.deepcopy(envelope)
                result = altered["adaptive_result"]
                if field == "lead_order":
                    result["adaptive_private_state"]["selected_adaptive_leads"][1:] = reversed(
                        result["adaptive_private_state"]["selected_adaptive_leads"][1:]
                    )
                elif field == "threshold":
                    result["adaptive_support_receipt"][
                        "minimum_alternative_posterior"
                    ] = 0.7
                    receipt = result["adaptive_support_receipt"]
                    receipt.pop("receipt_sha256")
                    receipt["receipt_sha256"] = payload_sha256(receipt)
                else:
                    altered["effect_delta_receipt"][
                        "additional_hosted_search_attempts"
                    ] = 1
                    effect = altered["effect_delta_receipt"]
                    effect.pop("receipt_sha256")
                    effect["receipt_sha256"] = payload_sha256(effect)
                result.pop("result_sha256")
                result["result_sha256"] = payload_sha256(result)
                altered.pop("envelope_payload_sha256")
                altered["envelope_payload_sha256"] = payload_sha256(altered)
                with self.assertRaises(ValueError):
                    validate_envelope(altered)


if __name__ == "__main__":
    unittest.main()
