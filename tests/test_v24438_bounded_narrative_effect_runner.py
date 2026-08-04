from __future__ import annotations

import copy
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256  # noqa: E402
from deepwide_agent.v24438_bounded_narrative_effect_runner import (  # noqa: E402
    FAILURE_NAME,
    MAXIMUM_PROVIDER_EFFECT_SECONDS,
    MODEL_NAME,
    RESULT_NAME,
    SEARCH_NAME,
    TRANSPORT_NAME,
    build_envelope,
    run_and_persist_bounded_narrative_task,
    run_v24438_task,
    validate_effect_timeout_contract,
    validate_envelope,
    validate_observed_bundle,
)
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import SEED, TASK  # noqa: E402
from test_v24412_receipt_snapshot_diagnosis import AdvancingClock  # noqa: E402
from test_v24430_title_anchor_effect_runner import (  # noqa: E402
    TitleDeadlineSearch,
    clients as parent_clients,
)


class NarrativeDeadlineSearch(TitleDeadlineSearch):
    def fetch_urls(self, requests_):
        batches = super().fetch_urls(requests_)
        if self.fetch_invocations == 3:
            for batch in batches:
                for result in batch["results"]:
                    result["raw_content"] = (
                        "The product was founded in 2025 and later expanded."
                    )
        return batches


def clients(output: Path, clock: AdvancingClock):
    model, original_search = parent_clients(output, clock)
    model.inner.timeout = MAXIMUM_PROVIDER_EFFECT_SECONDS
    search = NarrativeDeadlineSearch(clock, deadline=300)
    search.timeout = MAXIMUM_PROVIDER_EFFECT_SECONDS
    search.static_search_timeout_seconds = MAXIMUM_PROVIDER_EFFECT_SECONDS
    del original_search
    return model, search


def writer(directory: Path):
    def write(name: str, value) -> None:
        path = directory / name
        descriptor = os.open(
            path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
        )
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(dict(value), handle, ensure_ascii=False, sort_keys=True)
            handle.write("\n")

    return write


class V24438BoundedNarrativeEffectRunnerTests(unittest.TestCase):
    def make_directory(self) -> Path:
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        self.addCleanup(temporary.cleanup)
        return Path(temporary.name)

    def run_case(self):
        output = self.make_directory()
        clock = AdvancingClock()
        model, search = clients(output, clock)
        outcome = run_v24438_task(
            TASK,
            model=model,
            search=search,
            partition_seed_sha256=SEED,
            limits=limits(),
            monotonic=clock,
        )
        return outcome, model, search, output

    def test_bounded_narrative_recovery_gets_decision_credit(self) -> None:
        outcome, model, search, _ = self.run_case()
        envelope = build_envelope(outcome)
        validate_envelope(envelope)
        validate_observed_bundle(
            envelope,
            model_slot_receipt=outcome.model_slot_receipt,
            transport_health=outcome.transport_health,
            search_single_shot_receipt=outcome.search_single_shot_receipt,
            expected_cap=2,
        )
        receipt = outcome.narrative_title_result["narrative_recovery_receipt"]
        contract = outcome.effect_timeout_contract
        self.assertEqual(contract["model_provider_timeout_seconds"], 70.0)
        self.assertEqual(contract["hosted_search_timeout_seconds"], 70.0)
        self.assertEqual(receipt["narrative_projection_count"], 2)
        self.assertEqual(receipt["narrative_recovered_safe_change_count"], 1)
        self.assertGreater(
            receipt["narrative_recovered_decision_credit_total_nats"], 0
        )
        self.assertFalse(outcome.effect_equivalence_receipt["external_effect_detected"])
        self.assertEqual(model.acquisitions, 2)
        self.assertEqual(search.fetch_invocations, 3)

    def test_effect_cap_drift_fails_before_any_external_effect(self) -> None:
        for owner in ("model", "search"):
            with self.subTest(owner=owner):
                output = self.make_directory()
                clock = AdvancingClock()
                model, search = clients(output, clock)
                if owner == "model":
                    model.inner.timeout = MAXIMUM_PROVIDER_EFFECT_SECONDS + 1
                else:
                    search.static_search_timeout_seconds = (
                        MAXIMUM_PROVIDER_EFFECT_SECONDS + 1
                    )
                with self.assertRaises(ValueError):
                    run_v24438_task(
                        TASK,
                        model=model,
                        search=search,
                        partition_seed_sha256=SEED,
                        limits=limits(),
                        monotonic=clock,
                    )
                self.assertEqual(model.acquisitions, 0)
                self.assertEqual(search.calls, 0)
                self.assertEqual(search.fetch_calls, 0)

    def test_privileged_input_is_rejected_before_effect(self) -> None:
        output = self.make_directory()
        clock = AdvancingClock()
        model, search = clients(output, clock)
        with self.assertRaises(ValueError):
            run_v24438_task(
                {**TASK, "category": "forbidden"},
                model=model,
                search=search,
                partition_seed_sha256=SEED,
                limits=limits(),
                monotonic=clock,
            )
        self.assertEqual(model.acquisitions, 0)
        self.assertEqual(search.calls, 0)
        self.assertEqual(search.fetch_calls, 0)

    def test_timeout_contract_parent_or_narrative_tamper_fails(self) -> None:
        outcome, _, _, _ = self.run_case()
        envelope = build_envelope(outcome)
        for field in ("timeout", "parent", "narrative", "effect"):
            with self.subTest(field=field):
                altered = copy.deepcopy(envelope)
                if field == "timeout":
                    altered["effect_timeout_contract"][
                        "hosted_search_timeout_seconds"
                    ] += 1
                    contract = altered["effect_timeout_contract"]
                    contract.pop("contract_sha256")
                    contract["contract_sha256"] = payload_sha256(contract)
                elif field == "parent":
                    altered["parent_envelope"]["title_anchor_result"][
                        "title_anchor_recovery_receipt"
                    ]["additional_fetch_calls"] = 1
                elif field == "narrative":
                    altered["narrative_title_result"][
                        "narrative_recovery_receipt"
                    ]["additional_fetch_calls"] = 1
                else:
                    altered["effect_equivalence_receipt"][
                        "model_remaining_seconds_after"
                    ] += 0.001
                altered.pop("envelope_payload_sha256")
                altered["envelope_payload_sha256"] = payload_sha256(altered)
                with self.assertRaises((ValueError, RuntimeError)):
                    validate_envelope(altered)

    def test_success_persists_post_recovery_terminal_receipts(self) -> None:
        output = self.make_directory()
        clock = AdvancingClock()
        model, search = clients(output, clock)
        outcome = run_and_persist_bounded_narrative_task(
            TASK,
            model_factory=lambda: model,
            search_factory=lambda: search,
            partition_seed_sha256=SEED,
            limits=limits(),
            monotonic=clock,
            expected_model_cap=2,
            writer=writer(output),
        )
        for name in (MODEL_NAME, TRANSPORT_NAME, SEARCH_NAME, RESULT_NAME):
            self.assertTrue((output / name).is_file())
        self.assertFalse((output / FAILURE_NAME).exists())
        self.assertEqual(
            json.loads((output / MODEL_NAME).read_text(encoding="utf-8")),
            outcome.model_slot_receipt,
        )

    def test_recovery_failure_preserves_partial_effect_receipts(self) -> None:
        output = self.make_directory()
        clock = AdvancingClock()
        model, search = clients(output, clock)
        with patch(
            "deepwide_agent.v24438_bounded_narrative_effect_runner.recover_narrative_title_uncertainty",
            side_effect=RuntimeError("private narrative detail"),
        ):
            with self.assertRaises(RuntimeError):
                run_and_persist_bounded_narrative_task(
                    TASK,
                    model_factory=lambda: model,
                    search_factory=lambda: search,
                    partition_seed_sha256=SEED,
                    limits=limits(),
                    monotonic=clock,
                    expected_model_cap=2,
                    writer=writer(output),
                )
        for name in (MODEL_NAME, TRANSPORT_NAME, SEARCH_NAME, FAILURE_NAME):
            self.assertTrue((output / name).is_file())
        self.assertFalse((output / RESULT_NAME).exists())
        snapshot = json.loads((output / FAILURE_NAME).read_text(encoding="utf-8"))
        self.assertEqual(snapshot["failure_stage"], "runtime")
        self.assertNotIn("private narrative detail", json.dumps(snapshot))

    def test_contract_reseal_cannot_raise_cap(self) -> None:
        outcome, _, _, _ = self.run_case()
        contract = copy.deepcopy(outcome.effect_timeout_contract)
        contract["maximum_provider_effect_seconds"] += 1
        contract.pop("contract_sha256")
        contract["contract_sha256"] = payload_sha256(contract)
        with self.assertRaises(ValueError):
            validate_effect_timeout_contract(contract)


if __name__ == "__main__":
    unittest.main()
