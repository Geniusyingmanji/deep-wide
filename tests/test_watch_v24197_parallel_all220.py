from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.watch_v24197_parallel_all220 import run_cycle


VERIFIED = {
    "sha256": "p" * 64,
    "value": {
        "decision_contract_sha256": "d" * 64,
        "control_surface": {"manifest_sha256": "m" * 64},
        "capacity_input": {"parent_protocol_sha256": "q" * 64},
        "execution": {
            "state_path": "outputs/v24197_parallel_all220_watcher_state_v1_20260731.json"
        },
    },
}


class WatchV24197ParallelAll220Tests(unittest.TestCase):
    def test_bootstrap_validates_in_place_without_reexec(self) -> None:
        source = (
            Path(__file__).parents[1]
            / "scripts/watch_v24197_parallel_all220.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("os.execve", source)
        self.assertIn("V2.41.97 watcher requires python -I -B", source)
        self.assertIn("V2.41.97 control bytes drifted", source)

    def _run_cycle(self, root: Path, *, activation=None):
        with mock.patch(
            "scripts.watch_v24197_parallel_all220.ROOT", root
        ), mock.patch(
            "scripts.watch_v24197_parallel_all220.validate_protocol",
            return_value=VERIFIED,
        ), mock.patch(
            "scripts.watch_v24197_parallel_all220._activation",
            return_value=activation,
        ):
            return run_cycle(root, now=1)

    def test_missing_activation_reads_no_capacity_or_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            value = self._run_cycle(Path(directory))
        self.assertEqual(value["status"], "waiting_for_execution_activation")
        self.assertFalse(value["capacity_pair_opened"])
        self.assertFalse(value["candidate_bundle_opened"])
        self.assertFalse(value["candidate_manifest_bytes_hashed"])
        self.assertFalse(value["benchmark_forward_or_full220_launch_allowed"])

    def test_activated_pre_capacity_wait_is_zero_side_effect(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            value = self._run_cycle(root, activation={"sha256": "a" * 64})
            self.assertFalse((root / "results/v24197_parallel_all220_plan_v1_20260731.json").exists())
        self.assertEqual(value["status"], "waiting_for_capacity_freeze")
        self.assertFalse(value["shared_api_lease_acquired"])
        self.assertFalse(value["network_model_search_fetch_evaluator_or_api_called"])

    def test_capacity_pair_without_bundle_waits_without_opening_ids(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in (
                "results/v24196_capacity_ladder_report_v1_20260731.json",
                "results/v24196_next_fresh_all220_capacity_freeze_v1_20260731.json",
            ):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("{}", encoding="utf-8")
            with mock.patch(
                "scripts.watch_v24197_parallel_all220.ROOT", root
            ), mock.patch(
                "scripts.watch_v24197_parallel_all220.validate_protocol",
                return_value=VERIFIED,
            ), mock.patch(
                "scripts.watch_v24197_parallel_all220._activation",
                return_value={"sha256": "a" * 64},
            ), mock.patch(
                "scripts.watch_v24197_parallel_all220.load_capacity_pair",
                return_value=(
                    {"selected": 4, "workers": 2, "shards": 2},
                    {},
                    {"report_sha256": "r" * 64, "freeze_sha256": "f" * 64},
                ),
            ):
                value = run_cycle(root, now=1)
        self.assertEqual(value["status"], "waiting_for_candidate_execution_bundle")
        self.assertTrue(value["capacity_pair_opened"])
        self.assertFalse(value["opaque_id_files_opened"])

    def test_plan_creation_never_authorizes_forward(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in (
                "results/v24196_capacity_ladder_report_v1_20260731.json",
                "results/v24196_next_fresh_all220_capacity_freeze_v1_20260731.json",
                "results/v24197_fresh_all220_execution_bundle_v1_20260731.json",
            ):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("{}", encoding="utf-8")
            plan = {
                "role": "v24197_capacity_bound_fresh_all220_parallel_plan",
                "full220_launch_allowed": False,
            }
            from deepwide_agent.v24197_parallel_all220 import payload_sha256

            plan["plan_payload_sha256"] = payload_sha256(plan)
            with mock.patch(
                "scripts.watch_v24197_parallel_all220.ROOT", root
            ), mock.patch(
                "scripts.watch_v24197_parallel_all220.validate_protocol",
                return_value=VERIFIED,
            ), mock.patch(
                "scripts.watch_v24197_parallel_all220._activation",
                return_value={"sha256": "a" * 64},
            ), mock.patch(
                "scripts.watch_v24197_parallel_all220.load_capacity_pair",
                return_value=(
                    {"selected": 4, "workers": 2, "shards": 2},
                    {},
                    {"report_sha256": "r" * 64, "freeze_sha256": "f" * 64},
                ),
            ), mock.patch(
                "scripts.watch_v24197_parallel_all220._recompute_plan",
                return_value=(
                    plan,
                    {"selected": 4, "workers": 2, "shards": 2},
                    {},
                    {"report_sha256": "r" * 64, "freeze_sha256": "f" * 64},
                ),
            ):
                value = run_cycle(root, now=1)
                written = json.loads(
                    (
                        root
                        / "results/v24197_parallel_all220_plan_v1_20260731.json"
                    ).read_text(encoding="utf-8")
                )
        self.assertEqual(value["status"], "complete_parallel_plan_frozen")
        self.assertFalse(value["benchmark_forward_or_full220_launch_allowed"])
        self.assertFalse(written["full220_launch_allowed"])

    def test_existing_plan_is_live_recomputed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in (
                "results/v24196_capacity_ladder_report_v1_20260731.json",
                "results/v24196_next_fresh_all220_capacity_freeze_v1_20260731.json",
                "results/v24197_fresh_all220_execution_bundle_v1_20260731.json",
            ):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("{}", encoding="utf-8")
            plan_path = root / "results/v24197_parallel_all220_plan_v1_20260731.json"
            plan_path.write_text(
                json.dumps({
                    "role": "v24197_capacity_bound_fresh_all220_parallel_plan",
                    "full220_launch_allowed": False,
                    "plan_payload_sha256": "forged",
                }),
                encoding="utf-8",
            )
            with mock.patch(
                "scripts.watch_v24197_parallel_all220.ROOT", root
            ), mock.patch(
                "scripts.watch_v24197_parallel_all220.validate_protocol",
                return_value=VERIFIED,
            ), mock.patch(
                "scripts.watch_v24197_parallel_all220._activation",
                return_value={"sha256": "a" * 64},
            ), mock.patch(
                "scripts.watch_v24197_parallel_all220._recompute_plan",
                return_value=({"different": True}, {}, {}, {}),
            ), self.assertRaisesRegex(RuntimeError, "differs from live replay"):
                run_cycle(root, now=1)

    def test_plan_before_activation_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = root / "results/v24197_parallel_all220_plan_v1_20260731.json"
            plan.parent.mkdir(parents=True)
            plan.write_text("{}", encoding="utf-8")
            with mock.patch(
                "scripts.watch_v24197_parallel_all220.ROOT", root
            ), mock.patch(
                "scripts.watch_v24197_parallel_all220.validate_protocol",
                return_value=VERIFIED,
            ), mock.patch(
                "scripts.watch_v24197_parallel_all220._activation",
                return_value=None,
            ), self.assertRaisesRegex(RuntimeError, "before activation"):
                run_cycle(root, now=1)

    def test_live_activation_validation_is_required(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "results/v24197_parallel_all220_activation_v1_20260731.json"
            path.parent.mkdir(parents=True)
            path.write_text("{}", encoding="utf-8")
            with mock.patch(
                "scripts.watch_v24197_parallel_all220.validate_activation",
                side_effect=RuntimeError("PID reused"),
            ), self.assertRaisesRegex(RuntimeError, "PID reused"):
                from scripts.watch_v24197_parallel_all220 import _activation

                _activation(root, "p" * 64)


if __name__ == "__main__":
    unittest.main()
