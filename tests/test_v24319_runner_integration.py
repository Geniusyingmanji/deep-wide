from __future__ import annotations

import copy
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

from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import POOL_ID  # noqa: E402
from deepwide_agent.v24272_two_wave_entropy_voc import TwoWavePolicy  # noqa: E402
from deepwide_agent.v24294_staged_reserve import StagedReservePolicy  # noqa: E402
from deepwide_agent.v24313_runner_integration import build_deadline_model  # noqa: E402
from deepwide_agent.v24316_deadline_search import (  # noqa: E402
    DeadlineAwareNativeSearchClient,
)
from deepwide_agent.v24318_deadline_conservation_runtime import MODEL_FIELD  # noqa: E402
from deepwide_agent.v24319_runner_integration import (  # noqa: E402
    PARENT_BOUNDS_FIELD,
    build_envelope,
    project_parent_failure,
    run_v24319_task,
    validate_cross_artifacts,
    validate_parent_effect_bounds,
    validate_projected_parent_result,
)


class Clock:
    def __init__(self, value: float = 100.0) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value

    def sleep(self, seconds: float) -> None:
        self.value += float(seconds)


class InnerModel:
    def __init__(self) -> None:
        self.values = [
            json.dumps(
                {
                    "columns": ["Name", "Date"],
                    "queries": ["one", "two", "three", "four"],
                }
            ),
            "| Name | Date |\n| --- | --- |\n| A | 2026 |",
        ]
        self.requests = self.attempts = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0
        self.deadline_failures = 0

    def complete(self, *_args, **_kwargs):
        self.requests += 1
        self.attempts += 1
        self.input_tokens += 10
        self.output_tokens += 5
        self.total_tokens += 15
        return SimpleNamespace(text=self.values.pop(0))


class SyntheticDeadlineSearch(DeadlineAwareNativeSearchClient):
    def __init__(self, clock: Clock, *, deadline: float, expire_after_fetch: bool = False):
        super().__init__(
            "http://unused.invalid/responses",
            "synthetic",
            timeout=180,
            max_retries=2,
            fetch_pages=False,
            max_workers=1,
            fetch_workers=1,
            hard_fetch_deadline_seconds=25,
            absolute_deadline=deadline,
            cleanup_reserve_seconds=5,
            minimum_attempt_seconds=0.01,
            monotonic=clock,
            sleeper=clock.sleep,
        )
        self.clock = clock
        self.expire_after_fetch = expire_after_fetch
        self.search_invocations = 0

    def search_many(self, queries, **_kwargs):
        values = list(queries)
        self.search_invocations += 1
        self._increment("calls")
        self._increment("tool_calls")
        return [
            {
                "query": query,
                "answer": "",
                "results": [
                    {
                        "url": f"https://synthetic-{self.search_invocations}-{index}.invalid/page",
                        "title": "synthetic",
                        "content": "untrusted snippet",
                    }
                    for index in range(3)
                ],
            }
            for query in values
        ]

    def fetch_urls(self, requests_):
        values = list(requests_)
        self._increment("fetch_calls", len(values))
        batches = [
            {
                "query": item["query"],
                "results": [
                    {
                        "url": item["url"],
                        "title": "synthetic",
                        "raw_content": "public synthetic page " + "x" * 1000,
                    }
                ],
            }
            for item in values
        ]
        if self.expire_after_fetch:
            self.clock.value = 221.0
        return batches


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


def _task() -> dict[str, str]:
    return {
        "opaque_id": "task_0123456789abcdef01234567",
        "question": "Return one table. The column names are: Name, Date.",
    }


class V24319RunnerIntegrationTests(unittest.TestCase):
    def _clients(self, output: Path, clock: Clock, *, deadline: float, expire=False):
        model = build_deadline_model(
            url="http://unused.invalid/responses",
            model_name="synthetic",
            reasoning_effort="low",
            service_tier="",
            static_timeout_seconds=180,
            max_retries=2,
            slot_directory=_slots(output),
            output_root=output,
            slot_cap=2,
            pool_id=POOL_ID,
            absolute_deadline=deadline,
            cleanup_reserve_seconds=5,
            minimum_attempt_seconds=0.01,
            monotonic=clock,
            sleeper=clock.sleep,
            inner=InnerModel(),
        )
        search = SyntheticDeadlineSearch(
            clock, deadline=deadline, expire_after_fetch=expire
        )
        return model, search

    def test_both_arms_share_one_deadline_and_cross_artifact_conservation(self) -> None:
        for arm in ("baseline", "candidate"):
            with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
                output = Path(directory)
                clock = Clock()
                model, search = self._clients(output, clock, deadline=300)
                outcome = run_v24319_task(
                    _task(),
                    arm=arm,
                    model=model,
                    search=search,
                    limits=_limits(),
                    two_wave_policy=TwoWavePolicy(),
                    reserve_policy=StagedReservePolicy()
                    if arm == "candidate"
                    else None,
                    monotonic=clock,
                )
                envelope = build_envelope(outcome, arm=arm)
                self.assertEqual(envelope["result"]["completion_kind"], "primary")
                receipt = envelope["result"][MODEL_FIELD]
                self.assertEqual(
                    receipt["logical_admissions_total"],
                    outcome.model_slot_receipt["acquisitions"]
                    + outcome.model_slot_receipt["slot_timeouts"],
                )

    def test_slot_rejections_are_valid_child_results_not_parent_failures(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            output = Path(directory)
            clock = Clock()
            model, search = self._clients(output, clock, deadline=100.10)
            handles = [
                open(output / "slots" / f"slot_{index:02d}.lock", "r+", encoding="utf-8")
                for index in range(1, 3)
            ]
            for handle in handles:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            try:
                outcome = run_v24319_task(
                    _task(),
                    arm="candidate",
                    model=model,
                    search=search,
                    limits=_limits(),
                    two_wave_policy=TwoWavePolicy(),
                    reserve_policy=StagedReservePolicy(),
                    monotonic=clock,
                )
            finally:
                for handle in handles:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                    handle.close()
            receipt = outcome.result[MODEL_FIELD]
            self.assertGreater(receipt["pre_provider_rejections_total"], 0)
            self.assertEqual(
                receipt["pre_provider_rejections_total"],
                outcome.model_slot_receipt["slot_timeouts"],
            )
            self.assertTrue(receipt["effect_count_complete"])

    def test_cache_deferral_remains_a_valid_child_result(self) -> None:
        for arm in ("baseline", "candidate"):
            with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
                output = Path(directory)
                clock = Clock()
                model, search = self._clients(
                    output, clock, deadline=300, expire=True
                )
                outcome = run_v24319_task(
                    _task(),
                    arm=arm,
                    model=model,
                    search=search,
                    limits=_limits(),
                    two_wave_policy=TwoWavePolicy(),
                    reserve_policy=StagedReservePolicy()
                    if arm == "candidate"
                    else None,
                    monotonic=clock,
                )
                self.assertGreater(
                    outcome.result["v24318_cache_conservation"][
                        "deadline_deferred_pages"
                    ],
                    0,
                )

    def test_cross_artifact_tamper_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            output = Path(directory)
            clock = Clock()
            model, search = self._clients(output, clock, deadline=300)
            outcome = run_v24319_task(
                _task(),
                arm="baseline",
                model=model,
                search=search,
                limits=_limits(),
                two_wave_policy=TwoWavePolicy(),
                monotonic=clock,
            )
            altered = copy.deepcopy(outcome.model_slot_receipt)
            altered["slot_timeouts"] += 1
            from deepwide_agent.v24263_global_model_limiter import payload_sha256

            altered.pop("receipt_payload_sha256")
            altered["receipt_payload_sha256"] = payload_sha256(altered)
            with self.assertRaises(ValueError):
                validate_cross_artifacts(
                    outcome.result,
                    arm="baseline",
                    model_slot_receipt=altered,
                    transport_health=outcome.transport_health,
                    expected_cap=2,
                )

    def test_parent_timeout_projection_preserves_incomplete_bounds(self) -> None:
        progress = {
            MODEL_FIELD: {
                "artifact_version": 1,
                "role": "v24318_model_admission_conservation_receipt",
                "policy_id": "v24318_deadline_conservation_runtime_v1",
                "arm": "candidate",
                "model_call_cap": 3,
                "logical_admissions_by_stage": {
                    "plan": 1,
                    "synthesis_initial": 0,
                    "synthesis_recovery": 0,
                    "repair": 0,
                },
                "provider_requests_by_stage": {
                    "plan": 1,
                    "synthesis_initial": 0,
                    "synthesis_recovery": 0,
                    "repair": 0,
                },
                "provider_attempts_by_stage": {
                    "plan": 2,
                    "synthesis_initial": 0,
                    "synthesis_recovery": 0,
                    "repair": 0,
                },
                "pre_provider_rejections_by_stage": {
                    "plan": 0,
                    "synthesis_initial": 0,
                    "synthesis_recovery": 0,
                    "repair": 0,
                },
                "logical_admissions_total": 1,
                "provider_requests_total": 1,
                "provider_attempts_total": 2,
                "pre_provider_rejections_total": 0,
                "synthesis_initial_model_request_error": False,
                "synthesis_recovery_attempted": False,
                "synthesis_recovery_succeeded": False,
                "synthesis_recovery_model_request_error": False,
                "repair_blocked_after_recovery": False,
                "effect_count_complete": True,
                "effect_attribution_complete": True,
                "fourth_model_effect": False,
                "question_prompt_response_prediction_answer_opaque_id_or_credential_emitted": False,
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
                "benchmark_launch_or_evaluator_authorized": False,
            },
            "model_cost": {"requests": 1, "attempts": 2},
        }
        result = project_parent_failure(
            _task(),
            limits=_limits(),
            completion_kind="hard_deadline_fallback",
            failure_type="hard_deadline_timeout",
            elapsed_seconds=195,
            progress=progress,
            model_slot_receipt=None,
            expected_cap=2,
        )
        validate_projected_parent_result(result)
        bounds = result[PARENT_BOUNDS_FIELD]
        validate_parent_effect_bounds(bounds)
        self.assertFalse(bounds["effect_count_complete"])
        self.assertEqual(bounds["logical_admissions_lower_bound"], 1)
        self.assertEqual(bounds["logical_admissions_upper_bound"], 3)

    def test_parent_projection_without_any_receipt_does_not_guess_zero(self) -> None:
        result = project_parent_failure(
            _task(),
            limits=_limits(),
            completion_kind="worker_failure_fallback",
            failure_type="parent_subprocess_exception",
            elapsed_seconds=0,
            progress=None,
            model_slot_receipt=None,
            expected_cap=2,
        )
        bounds = result[PARENT_BOUNDS_FIELD]
        self.assertEqual(bounds["logical_admissions_lower_bound"], 0)
        self.assertEqual(bounds["logical_admissions_upper_bound"], 3)
        self.assertFalse(bounds["effect_count_complete"])

    def test_privileged_input_and_misaligned_deadline_fail_before_effect(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            output = Path(directory)
            clock = Clock()
            model, search = self._clients(output, clock, deadline=300)
            with self.assertRaises(ValueError):
                run_v24319_task(
                    {**_task(), "question_type": "forbidden"},
                    arm="baseline",
                    model=model,
                    search=search,
                    limits=_limits(),
                    two_wave_policy=TwoWavePolicy(),
                    monotonic=clock,
                )
            self.assertEqual(model.acquisitions, 0)
            self.assertEqual(search.search_invocations, 0)
            search.absolute_deadline += 1
            with self.assertRaisesRegex(ValueError, "deadline identity"):
                run_v24319_task(
                    _task(),
                    arm="baseline",
                    model=model,
                    search=search,
                    limits=_limits(),
                    two_wave_policy=TwoWavePolicy(),
                    monotonic=clock,
                )
            self.assertEqual(model.acquisitions, 0)


if __name__ == "__main__":
    unittest.main()
