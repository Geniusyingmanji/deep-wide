from __future__ import annotations

import fcntl
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.clients import ResponsesClient  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24272_two_wave_entropy_voc import TwoWavePolicy  # noqa: E402
from deepwide_agent.v24294_staged_reserve import StagedReservePolicy  # noqa: E402
from deepwide_agent.v24310_paired_dev_runtime import RECEIPT_FIELD  # noqa: E402
from deepwide_agent.v24313_runner_integration import (  # noqa: E402
    build_deadline_model,
    run_v24313_task,
    validate_deadline_model_receipt,
)
from test_v24272_two_wave_retrieval import Clock  # noqa: E402
from test_v24289_low_coverage_rescue import TailSearch  # noqa: E402
from test_v24290_low_coverage_task_runtime import (  # noqa: E402
    FakeModel,
    TABLE,
    plan,
    task,
)


def _slots(root: Path) -> Path:
    value = root / "slots"
    value.mkdir()
    for index in range(1, 3):
        (value / f"slot_{index:02d}.lock").write_text(
            json.dumps({"slot": index}) + "\n", encoding="utf-8"
        )
    return value


def _limits() -> ScoreFirstLimits:
    return ScoreFirstLimits(
        wall_seconds=120,
        model_calls=3,
        search_queries=4,
        fetch_targets=10,
        search_results_per_query=3,
        evidence_chars=60_000,
        page_chars=5_000,
    )


class V24313RunnerIntegrationTests(unittest.TestCase):
    def test_both_arms_use_deadline_model_and_same_totality(self) -> None:
        for arm in ("baseline", "candidate"):
            with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
                output = Path(directory)
                slots = _slots(output)
                inner = FakeModel([plan(), TABLE])
                model = build_deadline_model(
                    url="http://invalid.local",
                    model_name="synthetic",
                    reasoning_effort="low",
                    service_tier="",
                    static_timeout_seconds=180,
                    max_retries=2,
                    slot_directory=slots,
                    output_root=output,
                    slot_cap=2,
                    pool_id="v24263_score_first_global_model_slots_v1",
                    absolute_deadline=time.monotonic() + 3,
                    cleanup_reserve_seconds=0.2,
                    minimum_attempt_seconds=0.01,
                    inner=inner,
                )
                result = run_v24313_task(
                    task(),
                    arm=arm,
                    model=model,
                    search=TailSearch(sparse=True, failed_fetches=8),
                    limits=_limits(),
                    two_wave_policy=TwoWavePolicy(),
                    reserve_policy=StagedReservePolicy()
                    if arm == "candidate"
                    else None,
                    monotonic=Clock(),
                )
                self.assertEqual(result["completion_kind"], "primary")
                self.assertTrue(result[RECEIPT_FIELD]["recovery_enabled"])
                receipt = model.receipt()
                validate_deadline_model_receipt(
                    receipt,
                    expected_cap=2,
                    expected_acquisitions=result["cost"]["model"]["requests"],
                )
                self.assertEqual(receipt["slot_timeouts"], 0)

    def test_static_responses_client_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            output = Path(directory)
            slots = _slots(output)
            with self.assertRaisesRegex(ValueError, "static-timeout"):
                build_deadline_model(
                    url="http://invalid.local",
                    model_name="synthetic",
                    reasoning_effort="low",
                    service_tier="",
                    static_timeout_seconds=180,
                    max_retries=2,
                    slot_directory=slots,
                    output_root=output,
                    slot_cap=2,
                    pool_id="v24263_score_first_global_model_slots_v1",
                    absolute_deadline=time.monotonic() + 1,
                    inner=ResponsesClient(
                        "http://invalid.local", "synthetic", timeout=180
                    ),
                )

    def test_two_held_slots_return_total_fallback_without_provider_effect(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            output = Path(directory)
            slots = _slots(output)
            handles = [
                open(slots / f"slot_{index:02d}.lock", "r+", encoding="utf-8")
                for index in range(1, 3)
            ]
            for handle in handles:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            try:
                inner = FakeModel([plan(), TABLE])
                model = build_deadline_model(
                    url="http://invalid.local",
                    model_name="synthetic",
                    reasoning_effort="low",
                    service_tier="",
                    static_timeout_seconds=180,
                    max_retries=2,
                    slot_directory=slots,
                    output_root=output,
                    slot_cap=2,
                    pool_id="v24263_score_first_global_model_slots_v1",
                    absolute_deadline=time.monotonic() + 0.16,
                    cleanup_reserve_seconds=0.08,
                    minimum_attempt_seconds=0.01,
                    inner=inner,
                )
                result = run_v24313_task(
                    task(),
                    arm="baseline",
                    model=model,
                    search=TailSearch(sparse=False),
                    limits=_limits(),
                    two_wave_policy=TwoWavePolicy(),
                )
                self.assertIn(
                    result["completion_kind"],
                    {"best_effort_fallback", "worker_failure_fallback"},
                )
                self.assertEqual(inner.requests, 0)
                self.assertGreaterEqual(model.receipt()["slot_timeouts"], 1)
                self.assertLessEqual(
                    result[RECEIPT_FIELD]["total_effects_admitted"], 3
                )
                self.assertFalse(result[RECEIPT_FIELD]["fourth_model_effect"])
            finally:
                for handle in handles:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                    handle.close()

    def test_privileged_input_rejected_before_any_effect(self) -> None:
        class Counter:
            requests = attempts = 0
            input_tokens = output_tokens = total_tokens = 0
            deadline_failures = 0

            def complete(self, *_args, **_kwargs):
                self.requests += 1
                return SimpleNamespace(text="should not happen")

        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            output = Path(directory)
            inner = Counter()
            model = build_deadline_model(
                url="http://invalid.local",
                model_name="synthetic",
                reasoning_effort="low",
                service_tier="",
                static_timeout_seconds=180,
                max_retries=2,
                slot_directory=_slots(output),
                output_root=output,
                slot_cap=2,
                pool_id="v24263_score_first_global_model_slots_v1",
                absolute_deadline=time.monotonic() + 1,
                inner=inner,
            )
            search = TailSearch(sparse=False)
            with self.assertRaises(ValueError):
                run_v24313_task(
                    {**task(), "question_type": "forbidden"},
                    arm="baseline",
                    model=model,
                    search=search,
                    limits=_limits(),
                    two_wave_policy=TwoWavePolicy(),
                )
            self.assertEqual(inner.requests, 0)
            self.assertEqual(search.search_invocations, 0)


if __name__ == "__main__":
    unittest.main()
