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
from deepwide_agent.v24447_third_source_entropy_to_decision import (  # noqa: E402
    MAXIMUM_ACTIVE_SOURCES,
    MAXIMUM_TOTAL_FETCHES,
    THRESHOLD_PARTITION_FIELDS,
    build_envelope,
    run_and_persist_v24447_task,
    run_v24447_task,
    select_third_source,
    validate_effect_delta_receipt,
    validate_envelope,
    validate_result,
)
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import SEED, TASK  # noqa: E402
from test_v24412_receipt_snapshot_diagnosis import AdvancingClock  # noqa: E402
from test_v24430_title_anchor_effect_runner import clients as title_clients  # noqa: E402
from test_v24438_bounded_narrative_effect_runner import (  # noqa: E402
    NarrativeDeadlineSearch,
)


KNOWN_BASELINE = """```markdown
| Name | Founding year |
| --- | --- |
| Alpha | 2024 |
| Beta | 2024 |
```"""


class ThreeSourceNarrativeSearch(NarrativeDeadlineSearch):
    def _request(self, queries):  # type: ignore[override]
        payload = super()._request(queries)
        if self.request_invocations == 3:
            payload["output"][0]["action"]["sources"].append(
                {
                    "type": "web_source",
                    "url": "https://active-alpha-three.example/record",
                    "title": "Alpha official history",
                }
            )
        return payload

    def fetch_urls(self, requests_):
        batches = super().fetch_urls(requests_)
        if self.fetch_invocations in {3, 4}:
            for batch in batches:
                for result in batch["results"]:
                    result["raw_content"] = (
                        "The product was founded in 2025 and later expanded."
                    )
        return batches


def clients(output: Path, clock: AdvancingClock, *, third: bool):
    model, old_search = title_clients(output, clock)
    model.inner.timeout = MAXIMUM_PROVIDER_EFFECT_SECONDS
    model.inner.baseline = KNOWN_BASELINE
    search_type = ThreeSourceNarrativeSearch if third else NarrativeDeadlineSearch
    search = search_type(clock, deadline=300)
    search.timeout = MAXIMUM_PROVIDER_EFFECT_SECONDS
    search.static_search_timeout_seconds = MAXIMUM_PROVIDER_EFFECT_SECONDS
    del old_search
    return model, search


class V24447ThirdSourceEntropyToDecisionTests(unittest.TestCase):
    def run_case(self, *, third: bool):
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        self.addCleanup(temporary.cleanup)
        clock = AdvancingClock()
        model, search = clients(Path(temporary.name), clock, third=third)
        outcome = run_v24447_task(
            TASK,
            model=model,
            search=search,
            partition_seed_sha256=SEED,
            limits=limits(),
            monotonic=clock,
        )
        validate_result(outcome.third_source_result)
        validate_envelope(build_envelope(outcome))
        return outcome, model, search

    def test_missing_third_lead_is_zero_effect_noop(self) -> None:
        outcome, model, search = self.run_case(third=False)
        receipt = outcome.third_source_result["third_source_recovery_receipt"]
        effect = validate_effect_delta_receipt(outcome.effect_delta_receipt)
        self.assertIsNone(select_third_source(outcome.parent.narrative_title_result))
        self.assertEqual(receipt["third_source_candidate_count"], 0)
        self.assertEqual(receipt["additional_fetch_calls"], 0)
        self.assertEqual(effect["additional_fetch_effects"], 0)
        self.assertEqual(effect["additional_model_acquisitions"], 0)
        self.assertEqual(effect["additional_hosted_search_attempts"], 0)
        self.assertEqual(model.acquisitions, 2)
        self.assertEqual(search.fetch_invocations, 3)
        self.assertEqual(receipt["safe_change_count"], 0)
        self.assertEqual(receipt["decision_credit_total_nats"], 0)

    def test_third_source_crosses_unchanged_known_baseline_gate(self) -> None:
        outcome, model, search = self.run_case(third=True)
        receipt = outcome.third_source_result["third_source_recovery_receipt"]
        effect = outcome.effect_delta_receipt
        self.assertEqual(receipt["active_source_cap"], MAXIMUM_ACTIVE_SOURCES)
        self.assertEqual(receipt["total_fetch_cap"], MAXIMUM_TOTAL_FETCHES)
        self.assertEqual(receipt["third_source_candidate_count"], 1)
        self.assertEqual(receipt["third_source_fetch_attempt_count"], 1)
        self.assertEqual(receipt["third_source_usable_page_count"], 1)
        self.assertEqual(receipt["additional_fetch_calls"], 1)
        self.assertEqual(receipt["additional_model_requests"], 0)
        self.assertEqual(receipt["additional_logical_queries"], 0)
        self.assertEqual(receipt["additional_search_batches"], 0)
        self.assertEqual(receipt["additional_provider_search_calls"], 0)
        self.assertEqual(effect["additional_fetch_effects"], 1)
        self.assertEqual(effect["additional_hosted_search_attempts"], 0)
        self.assertEqual(effect["additional_model_acquisitions"], 0)
        self.assertEqual(model.acquisitions, 2)
        self.assertEqual(search.fetch_invocations, 4)
        self.assertEqual(receipt["safe_change_count"], 1)
        self.assertGreater(receipt["decision_credit_total_nats"], 0)
        self.assertIn(
            "| Alpha | 2025 |",
            outcome.third_source_result["candidate_prediction"],
        )

    def test_threshold_partition_is_mutually_exclusive_and_conserved(self) -> None:
        for third in (False, True):
            with self.subTest(third=third):
                outcome, _, _ = self.run_case(third=third)
                receipt = outcome.third_source_result[
                    "third_source_recovery_receipt"
                ]
                partition = receipt["threshold_failure_partition"]
                self.assertEqual(tuple(partition), THRESHOLD_PARTITION_FIELDS)
                self.assertEqual(
                    sum(partition.values()), receipt["selected_target_count"]
                )
                self.assertEqual(
                    partition["safe_change_count"], receipt["safe_change_count"]
                )

    def test_private_or_effect_tamper_fails_closed(self) -> None:
        outcome, _, _ = self.run_case(third=True)
        envelope = build_envelope(outcome)
        for field in ("lead", "page", "threshold", "effect"):
            with self.subTest(field=field):
                altered = copy.deepcopy(envelope)
                if field == "lead":
                    altered["third_source_result"]["third_source_private_state"][
                        "selected_third_lead"
                    ]["title"] += " tamper"
                elif field == "page":
                    altered["third_source_result"]["third_source_private_state"][
                        "third_fetch_batches"
                    ][0]["results"][0]["raw_content"] += " tamper"
                elif field == "threshold":
                    altered["third_source_result"][
                        "third_source_recovery_receipt"
                    ]["minimum_alternative_posterior"] = 0.7
                else:
                    altered["effect_delta_receipt"][
                        "additional_hosted_search_attempts"
                    ] = 1
                altered.pop("envelope_payload_sha256")
                altered["envelope_payload_sha256"] = payload_sha256(altered)
                with self.assertRaises(ValueError):
                    validate_envelope(altered)

    def test_persisted_wrapper_writes_terminal_artifacts(self) -> None:
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        self.addCleanup(temporary.cleanup)
        output = Path(temporary.name)
        clock = AdvancingClock()
        model, search = clients(output, clock, third=True)
        artifacts = {}
        outcome = run_and_persist_v24447_task(
            TASK,
            model_factory=lambda: model,
            search_factory=lambda: search,
            partition_seed_sha256=SEED,
            limits=limits(),
            monotonic=clock,
            expected_model_cap=2,
            writer=lambda name, value: artifacts.__setitem__(name, copy.deepcopy(value)),
        )
        self.assertEqual(
            set(artifacts),
            {
                "model_slot_receipt.json",
                "transport_health.json",
                "search_single_shot_receipt.json",
                "result.json",
            },
        )
        self.assertEqual(
            artifacts["result.json"], build_envelope(outcome)
        )


if __name__ == "__main__":
    unittest.main()
