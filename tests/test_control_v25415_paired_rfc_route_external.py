from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import control_v25415_paired_rfc_route_external as target  # noqa: E402


def _fake_tests(fill: str = "a"):
    return {
        "expected": target.EXPECTED_TESTS,
        "observed": target.EXPECTED_TESTS,
        "passed": True,
        "suites": [
            {
                "pattern": pattern,
                "expected": expected,
                "observed": expected,
                "returncode": 0,
                "passed": True,
                "output_sha256": fill * 64,
            }
            for pattern, expected in target.TEST_SUITES
        ],
    }


class V25415PairedRfcRouteControlTests(unittest.TestCase):
    def test_contract_protocol_validates_without_launch_authority(self) -> None:
        value = target.contract.build_protocol(
            ROOT,
            now=1,
            tracked=False,
            require_pristine=False,
            build_audit_sha256="a" * 64,
        )
        self.assertEqual(
            target.contract.validate_protocol(ROOT, value, tracked=False), value
        )
        self.assertFalse(value["authorization"]["one_external_forward"])
        self.assertFalse(value["authorization"]["evaluator"])
        self.assertEqual(value["population"]["pair_count"], 20)
        self.assertEqual(value["population"]["task_count"], 40)
        self.assertTrue(value["execution"]["one_selected_parent_call_per_task"])
        self.assertTrue(value["execution"]["paired_tasks_have_independent_provider_effects"])
        self.assertFalse(value["execution"]["shared_model_sampling_or_shared_prefix_claimed"])
        self.assertTrue(value["execution"]["persist_frozen_prediction_text_for_postfreeze_quality"])
        self.assertTrue(
            value["postfreeze_quality_gate"][
                "membership_present_whole_table_exact_strictly_greater_than_absent"
            ]
        )

    def test_build_audit_authorizes_protocol_generation_only(self) -> None:
        with (
            mock.patch.object(target, "_tests", return_value=_fake_tests()),
            mock.patch.object(target, "_future_pristine", return_value=True),
            mock.patch.object(target, "_parent_barriers", return_value=True),
            mock.patch.object(target, "_lease_inactive", return_value=True),
            mock.patch.object(target.contract, "watcher_snapshot", return_value=[
                {"pid": pid, "start_ticks": ticks, "marker": marker}
                for pid, ticks, marker in target.contract.EXPECTED_WATCHERS
            ]),
        ):
            value = target.build_audit(now=1, require_clean=False)
        self.assertEqual(target.validate_build(value), value)
        self.assertTrue(
            value["authorization"]["protocol_generation_after_build_commit_push"]
        )
        self.assertFalse(value["authorization"]["external_forward"])
        self.assertFalse(value["authorization"]["postfreeze_quality"])

    def test_resealed_launch_credit_parent_or_quality_tamper_fails(self) -> None:
        with (
            mock.patch.object(target, "_tests", return_value=_fake_tests("b")),
            mock.patch.object(target, "_future_pristine", return_value=True),
            mock.patch.object(target, "_parent_barriers", return_value=True),
            mock.patch.object(target, "_lease_inactive", return_value=True),
            mock.patch.object(target.contract, "watcher_snapshot", return_value=[
                {"pid": pid, "start_ticks": ticks, "marker": marker}
                for pid, ticks, marker in target.contract.EXPECTED_WATCHERS
            ]),
        ):
            value = target.build_audit(now=1, require_clean=False)
        for kind in ("launch", "credit", "parent", "quality"):
            changed = copy.deepcopy(value)
            if kind == "launch":
                changed["authorization"]["external_forward"] = True
            elif kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            elif kind == "parent":
                changed["checks"]["runtime_and_population_parent_barriers_exact"] = False
            else:
                changed["postfreeze_quality_gate"][
                    "membership_present_whole_table_exact_strictly_greater_than_absent"
                ] = False
            changed.pop("audit_payload_sha256")
            changed = target.contract.seal(changed, "audit_payload_sha256")
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_build(changed)

    def test_control_source_has_no_evaluator_or_benchmark_entrypoint(self) -> None:
        source = (ROOT / target.contract.CONTROL).read_text(encoding="utf-8")
        for forbidden in (
            "run_official_eval_local(",
            "leaderboard_submit(",
            "run_exact220(",
            "fetch_rfc_truth(",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
