from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24313_runner_integration import build_deadline_model  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import POOL_ID  # noqa: E402
from deepwide_agent.v24409_structured_uncertainty_runner import (  # noqa: E402
    run_v24409_task,
)
from scripts import diagnose_v24412_v24411_receipt_snapshot_drift as target  # noqa: E402
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


class AdvancingClock:
    def __init__(self, value: float = 100.0) -> None:
        self.value = value

    def __call__(self) -> float:
        self.value += 0.001
        return self.value

    def sleep(self, seconds: float) -> None:
        self.value += float(seconds)


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
    return model, DeadlineUncertaintySearch(clock, deadline=300)


class V24412ReceiptSnapshotDiagnosisTests(unittest.TestCase):
    def test_advancing_clock_reproduces_false_external_effect_runtime_error(self) -> None:
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        self.addCleanup(temporary.cleanup)
        output = Path(temporary.name)
        clock = AdvancingClock()
        model, search = clients(output, clock)
        before_model = None
        before_transport = None
        before_search = None

        def pure_recovery(value):
            nonlocal before_model, before_transport, before_search
            before_model = copy.deepcopy(model.receipt())
            before_transport = copy.deepcopy(search.transport_health())
            before_search = copy.deepcopy(search.single_shot_receipt())
            return value

        with patch(
            "deepwide_agent.v24409_structured_uncertainty_runner.recover_structured_uncertainty",
            side_effect=pure_recovery,
        ):
            with self.assertRaisesRegex(RuntimeError, "external effect"):
                run_v24409_task(
                    TASK,
                    model=model,
                    search=search,
                    partition_seed_sha256=SEED,
                    limits=limits(),
                    monotonic=clock,
                )
        after_model = model.receipt()
        after_transport = search.transport_health()
        after_search = search.single_shot_receipt()
        self.assertIsNotNone(before_model)
        self.assertEqual(before_model["acquisitions"], after_model["acquisitions"])
        self.assertEqual(before_model["slot_timeouts"], after_model["slot_timeouts"])
        self.assertEqual(
            before_model["provider_deadline_failures"],
            after_model["provider_deadline_failures"],
        )
        self.assertGreater(
            before_model["remaining_seconds_at_receipt"],
            after_model["remaining_seconds_at_receipt"],
        )
        self.assertEqual(before_transport, after_transport)
        self.assertEqual(before_search, after_search)

    def test_public_report_identifies_single_runtime_branch_without_private_data(self) -> None:
        with (
            patch.object(target.base, "_tracked", return_value=True),
            patch.object(
                target.base,
                "_git",
                side_effect=lambda *args: ""
                if args == ("status", "--porcelain")
                else "same",
            ),
        ):
            report = target.build_report(now=0)
        self.assertTrue(report["diagnosis_valid"])
        self.assertEqual(
            report["diagnosis"],
            "whole_receipt_snapshot_equality_confuses_observation_time_drift_with_external_effect",
        )
        self.assertEqual(
            report["code_diagnosis"]["runtime_error_branches"],
            [
                {
                    "line": report["code_diagnosis"]["runtime_error_branches"][0][
                        "line"
                    ],
                    "message": "V2.44.09 recovery caused an external effect",
                }
            ],
        )
        self.assertFalse(
            report["closure"]["v24411_private_task_directories_reopened"]
        )
        self.assertFalse(report["authorization"]["external_probe_launch"])
        self.assertFalse(report["authorization"]["exact220"])


if __name__ == "__main__":
    unittest.main()
