from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.clients import ModelRequestError  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import (  # noqa: E402
    GlobalModelSlotLimiter,
    POOL_ID,
    validate_receipt as validate_slot_receipt,
)
from deepwide_agent.v24272_two_wave_entropy_voc import TwoWavePolicy  # noqa: E402
from deepwide_agent.v24294_staged_reserve import StagedReservePolicy  # noqa: E402
from deepwide_agent.v24299_synthesis_recovery import (  # noqa: E402
    run_v24299_task,
    run_v24299_total_task,
    validate_v24299_result,
    validate_v24299_total_result,
)
from test_v24272_two_wave_retrieval import Clock  # noqa: E402
from test_v24289_low_coverage_rescue import TailSearch  # noqa: E402
from test_v24290_low_coverage_task_runtime import (  # noqa: E402
    FakeModel,
    TABLE,
    plan,
    task,
)


def limits() -> ScoreFirstLimits:
    return ScoreFirstLimits(
        wall_seconds=120,
        model_calls=3,
        search_queries=4,
        fetch_targets=10,
        search_results_per_query=3,
        evidence_chars=60_000,
        page_chars=5_000,
    )


def call(arm: str, values: list[object], *, progress=None):
    return run_v24299_task(
        task(),
        arm=arm,
        model=FakeModel(values),
        search=TailSearch(sparse=True, failed_fetches=8),
        limits=limits(),
        two_wave_policy=TwoWavePolicy(),
        reserve_policy=StagedReservePolicy() if arm == "candidate" else None,
        monotonic=Clock(),
        progress=progress,
    )


class V24299SynthesisRecoveryTests(unittest.TestCase):
    def test_synthesis_model_request_error_uses_exact_third_slot(self) -> None:
        for arm in ("baseline", "candidate"):
            result = call(
                arm,
                [plan(), ModelRequestError("synthetic"), TABLE],
            )
            validate_v24299_result(result, arm)
            receipt = result["synthesis_recovery"]
            self.assertEqual(result["completion_kind"], "primary")
            self.assertEqual(result["budget"]["admitted_model_calls"], 3)
            self.assertEqual(result["cost"]["model"]["requests"], 3)
            self.assertEqual(receipt["total_effects_admitted"], 3)
            self.assertEqual(
                receipt["effects_by_stage"],
                {
                    "plan": 1,
                    "synthesis_initial": 1,
                    "synthesis_recovery": 1,
                    "repair": 0,
                },
            )
            self.assertTrue(receipt["synthesis_recovery_succeeded"])
            self.assertEqual(
                [event["stage"] for event in result["budget"]["events"] if event.get("effect") == "model"],
                ["plan", "synthesis", "synthesis_provider_recovery"],
            )
            synthesis = [
                event
                for event in result["telemetry"]["model_events"]
                if event["stage"] == "synthesis"
            ]
            self.assertEqual(synthesis[0]["requests_delta"], 2)

    def test_success_and_normal_repair_paths_are_not_retried(self) -> None:
        primary = call("candidate", [plan(), TABLE])
        self.assertEqual(primary["completion_kind"], "primary")
        self.assertEqual(primary["budget"]["admitted_model_calls"], 2)
        self.assertFalse(primary["synthesis_recovery"]["synthesis_recovery_attempted"])
        invalid = "not a table"
        repaired = call("candidate", [plan(), invalid, TABLE])
        self.assertEqual(repaired["completion_kind"], "repaired")
        self.assertEqual(repaired["budget"]["admitted_model_calls"], 3)
        self.assertEqual(repaired["synthesis_recovery"]["effects_by_stage"]["repair"], 1)
        self.assertFalse(repaired["synthesis_recovery"]["synthesis_recovery_attempted"])

    def test_recovered_invalid_output_blocks_fourth_provider_effect(self) -> None:
        result = call(
            "candidate",
            [plan(), ModelRequestError("synthetic"), "not a table"],
        )
        self.assertEqual(result["completion_kind"], "best_effort_fallback")
        receipt = result["synthesis_recovery"]
        self.assertTrue(receipt["synthesis_recovery_succeeded"])
        self.assertTrue(receipt["repair_blocked_after_recovery"])
        self.assertEqual(receipt["provider_requests_delta"], 3)
        self.assertEqual(receipt["effects_by_stage"]["repair"], 0)
        repair = [
            event
            for event in result["budget"]["events"]
            if event.get("stage") == "repair"
        ]
        self.assertEqual(repair, [{"stage": "repair", "effect": "model", "admitted": False}])

    def test_second_synthesis_failure_is_fail_closed_at_three_calls(self) -> None:
        result = call(
            "candidate",
            [
                plan(),
                ModelRequestError("first"),
                ModelRequestError("second"),
            ],
        )
        self.assertEqual(result["completion_kind"], "best_effort_fallback")
        receipt = result["synthesis_recovery"]
        self.assertTrue(receipt["synthesis_recovery_model_request_error"])
        self.assertFalse(receipt["synthesis_recovery_succeeded"])
        self.assertEqual(receipt["provider_requests_delta"], 3)
        self.assertEqual(result["budget"]["admitted_model_calls"], 3)

    def test_repair_or_arbitrary_failure_is_not_recovered(self) -> None:
        repair_failure = call(
            "candidate", [plan(), "not a table", ModelRequestError("repair")]
        )
        receipt = repair_failure["synthesis_recovery"]
        self.assertFalse(receipt["synthesis_recovery_attempted"])
        self.assertEqual(receipt["effects_by_stage"]["repair"], 1)
        arbitrary = call("candidate", [plan(), ValueError("not provider")])
        self.assertFalse(arbitrary["synthesis_recovery"]["synthesis_recovery_attempted"])
        self.assertEqual(arbitrary["cost"]["model"]["requests"], 2)

    def test_progress_and_receipt_are_content_free_and_tamper_fails(self) -> None:
        progress: list[dict] = []
        result = call(
            "candidate",
            [plan(), ModelRequestError("synthetic"), TABLE],
            progress=lambda value: progress.append(dict(value)),
        )
        self.assertTrue(progress)
        self.assertEqual(progress[-1]["admitted_model_calls"], 3)
        encoded = json.dumps(result["synthesis_recovery"])
        for forbidden in (task()["opaque_id"], "visible one", "Name", "| A |"):
            self.assertNotIn(forbidden, encoded)
        altered = copy.deepcopy(result)
        altered["synthesis_recovery"]["provider_requests_delta"] += 1
        with self.assertRaises(ValueError):
            validate_v24299_result(altered, "candidate")

    def test_real_global_slot_wrapper_matches_three_recovery_effects(self) -> None:
        output_root = ROOT / "outputs"
        with tempfile.TemporaryDirectory(dir=output_root) as directory:
            slots = Path(directory)
            for index in range(1, 3):
                (slots / f"slot_{index:02d}.lock").write_text("{}\n")
            inner = FakeModel([plan(), ModelRequestError("synthetic"), TABLE])
            model = GlobalModelSlotLimiter(
                inner,
                slot_directory=slots,
                output_root=output_root,
                slot_cap=2,
                pool_id=POOL_ID,
            )
            result = run_v24299_task(
                task(),
                arm="candidate",
                model=model,
                search=TailSearch(sparse=True, failed_fetches=8),
                limits=limits(),
                two_wave_policy=TwoWavePolicy(),
                reserve_policy=StagedReservePolicy(),
                monotonic=Clock(),
            )
            validate_v24299_result(result, "candidate")
            receipt = validate_slot_receipt(
                model.receipt(), expected_cap=2, expected_acquisitions=3
            )
            self.assertEqual(receipt["acquisitions"], result["cost"]["model"]["requests"])
            self.assertEqual(receipt["acquisitions"], 3)

    def test_total_boundary_and_privileged_input(self) -> None:
        fallback = run_v24299_total_task(
            task(),
            arm="candidate",
            model=FakeModel([KeyboardInterrupt()]),
            search=TailSearch(sparse=False),
            limits=limits(),
            two_wave_policy=TwoWavePolicy(),
            reserve_policy=StagedReservePolicy(),
            monotonic=Clock(),
        )
        self.assertEqual(validate_v24299_total_result(fallback, "candidate"), "fallback")
        model = FakeModel([plan(), TABLE])
        search = TailSearch(sparse=False)
        with self.assertRaises(ValueError):
            run_v24299_total_task(
                {**task(), "question_type": "forbidden"},
                arm="candidate",
                model=model,
                search=search,
                limits=limits(),
                two_wave_policy=TwoWavePolicy(),
                reserve_policy=StagedReservePolicy(),
            )
        self.assertEqual(model.requests, 0)
        self.assertEqual(search.search_invocations, 0)


if __name__ == "__main__":
    unittest.main()
