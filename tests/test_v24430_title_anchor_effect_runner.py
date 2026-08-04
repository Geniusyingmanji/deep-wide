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

from deepwide_agent.v24263_global_model_limiter import POOL_ID  # noqa: E402
from deepwide_agent.v24313_runner_integration import build_deadline_model  # noqa: E402
from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256  # noqa: E402
from deepwide_agent.v24430_title_anchor_effect_runner import (  # noqa: E402
    FAILURE_NAME,
    MODEL_NAME,
    RESULT_NAME,
    SEARCH_NAME,
    TRANSPORT_NAME,
    build_envelope,
    run_and_persist_title_anchor_task,
    run_v24430_task,
    validate_envelope,
    validate_observed_bundle,
)
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24343_semantic_active_runner import slots  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import (  # noqa: E402
    IdentityModel,
    SEED,
    TASK,
)
from test_v24391_uncertainty_active_evidence_runner import (  # noqa: E402
    DeadlineUncertaintySearch,
)
from test_v24412_receipt_snapshot_diagnosis import AdvancingClock  # noqa: E402


class TitleDeadlineSearch(DeadlineUncertaintySearch):
    def _request(self, queries):  # type: ignore[override]
        payload = super()._request(queries)
        if self.request_invocations == 3:
            sources = payload["output"][0]["action"]["sources"]
            sources[:] = [
                {
                    "type": "web_source",
                    "url": "https://active-alpha-one.example/record",
                    "title": "Alpha - official history",
                },
                {
                    "type": "web_source",
                    "url": "https://active-alpha-two.example/record",
                    "title": "Alpha | historical archive",
                },
            ]
        return payload

    def fetch_urls(self, requests_):
        batches = super().fetch_urls(requests_)
        if self.fetch_invocations == 3:
            for batch in batches:
                for result in batch["results"]:
                    result["raw_content"] = "Founded | 2025"
        return batches


def clients(output: Path, clock: AdvancingClock):
    model = build_deadline_model(
        url="http://unused.invalid/responses",
        model_name="synthetic",
        reasoning_effort="low",
        service_tier="",
        static_timeout_seconds=180,
        max_retries=2,
        slot_directory=slots(output),
        output_root=output,
        slot_cap=2,
        pool_id=POOL_ID,
        absolute_deadline=300,
        cleanup_reserve_seconds=5,
        minimum_attempt_seconds=0.01,
        monotonic=clock,
        sleeper=clock.sleep,
        inner=IdentityModel(),
    )
    return model, TitleDeadlineSearch(clock, deadline=300)


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


class V24430TitleAnchorEffectRunnerTests(unittest.TestCase):
    def make_directory(self) -> Path:
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        self.addCleanup(temporary.cleanup)
        return Path(temporary.name)

    def run_case(self):
        output = self.make_directory()
        clock = AdvancingClock()
        model, search = clients(output, clock)
        outcome = run_v24430_task(
            TASK,
            model=model,
            search=search,
            partition_seed_sha256=SEED,
            limits=limits(),
            monotonic=clock,
        )
        return outcome, model, search, output

    def test_title_recovery_is_effect_equivalent_and_gets_decision_credit(self) -> None:
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
        receipt = outcome.title_anchor_result["title_anchor_recovery_receipt"]
        equivalence = outcome.effect_equivalence_receipt
        self.assertEqual(receipt["title_anchor_projection_count"], 2)
        self.assertEqual(receipt["title_recovered_safe_change_count"], 1)
        self.assertGreater(receipt["title_recovered_decision_credit_total_nats"], 0)
        self.assertFalse(equivalence["external_effect_detected"])
        self.assertGreaterEqual(
            equivalence["model_remaining_seconds_before"],
            equivalence["model_remaining_seconds_after"],
        )
        self.assertEqual(model.acquisitions, 2)
        self.assertEqual(search.fetch_invocations, 3)

    def test_parent_title_or_effect_tamper_fails_closed(self) -> None:
        outcome, _, _, _ = self.run_case()
        envelope = build_envelope(outcome)
        for field in ("parent", "title", "effect"):
            with self.subTest(field=field):
                altered = copy.deepcopy(envelope)
                if field == "parent":
                    altered["parent_envelope"]["projection_observability_receipt"][
                        "page_count"
                    ] += 1
                elif field == "title":
                    altered["title_anchor_result"]["title_anchor_recovery_receipt"][
                        "additional_fetch_calls"
                    ] = 1
                else:
                    altered["effect_equivalence_receipt"][
                        "model_remaining_seconds_after"
                    ] += 0.001
                altered.pop("envelope_payload_sha256")
                altered["envelope_payload_sha256"] = payload_sha256(altered)
                with self.assertRaises(ValueError):
                    validate_envelope(altered)

    def test_privileged_input_is_rejected_before_effect(self) -> None:
        output = self.make_directory()
        clock = AdvancingClock()
        model, search = clients(output, clock)
        with self.assertRaises(ValueError):
            run_v24430_task(
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

    def test_success_persists_post_recovery_terminal_receipts(self) -> None:
        output = self.make_directory()
        clock = AdvancingClock()
        model, search = clients(output, clock)
        outcome = run_and_persist_title_anchor_task(
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
            "deepwide_agent.v24430_title_anchor_effect_runner.recover_title_anchor_uncertainty",
            side_effect=RuntimeError("private title detail"),
        ):
            with self.assertRaises(RuntimeError):
                run_and_persist_title_anchor_task(
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
        self.assertNotIn("private title detail", json.dumps(snapshot))


if __name__ == "__main__":
    unittest.main()
