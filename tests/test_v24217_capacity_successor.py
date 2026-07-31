from __future__ import annotations

import threading
import unittest
from types import SimpleNamespace

from deepwide_agent.v24194_capacity_ladder import (
    PROBE_EXPECTED_OUTPUT,
    PROBE_INPUT_UTF8_BYTES,
    ProbeSettings,
    run_capacity_ladder,
)
from deepwide_agent.v24217_capacity_successor import (
    build_freeze,
    build_report,
    payload_sha256,
    validate_freeze,
    validate_report,
)


class FakeClient:
    def __init__(self) -> None:
        self.lock = threading.Lock()

    def complete(self, system, user, *, max_output_tokens):
        return SimpleNamespace(
            text=PROBE_EXPECTED_OUTPUT,
            attempts=1,
            output_truncated=False,
            input_utf8_bytes=len((system + user).encode("utf-8")),
            request_body_bytes=PROBE_INPUT_UTF8_BYTES + 100,
            max_output_tokens=max_output_tokens,
        )


class V24217CapacitySuccessorTests(unittest.TestCase):
    @staticmethod
    def settings() -> ProbeSettings:
        return ProbeSettings(
            levels=(1, 2),
            waves_per_level=2,
            absolute_latency_ceiling_seconds=999,
            baseline_p95_multiplier=999,
            baseline_median_multiplier=999,
        )

    def test_report_and_freeze_recompute_neutral_capacity(self) -> None:
        settings = self.settings()
        measurement = run_capacity_ladder(FakeClient(), settings=settings)
        report = build_report(
            measurement,
            protocol={"path": "results/protocol.json", "sha256": "a" * 64},
            parent_package_gate={
                "path": "outputs/parent.json",
                "sha256": "b" * 64,
                "status": "complete_package_gate_go",
                "capacity_measurement_allowed": True,
                "all220_freeze_design_allowed": True,
                "contents_emitted": False,
            },
            execution_activation={
                "path": "results/activation.json",
                "sha256": "c" * 64,
            },
            shared_api_lease={
                "owner": "v24217_post_package_gate_neutral_capacity_v1",
                "purpose": "neutral_capacity_after_v24216_go_for_next_fresh_all220",
                "owner_purpose_pid_and_lock_holder_exact": True,
                "contents_emitted": False,
            },
            created_at_unix=1,
            expected_settings=settings,
        )
        derived = validate_report(
            report,
            expected_settings=settings,
            protocol_path="results/protocol.json",
            protocol_sha256="a" * 64,
        )
        self.assertEqual(derived["selected"], 2)
        freeze = build_freeze(
            report,
            expected_settings=settings,
            report_path="results/report.json",
            report_sha256="d" * 64,
            protocol_path="results/protocol.json",
            protocol_sha256="a" * 64,
            created_at_unix=2,
        )
        replay = validate_freeze(
            freeze,
            report=report,
            expected_settings=settings,
            report_path="results/report.json",
            report_sha256="d" * 64,
            protocol_path="results/protocol.json",
            protocol_sha256="a" * 64,
        )
        self.assertEqual(replay["selected"], 2)
        self.assertFalse(freeze["full220_launch_allowed"])
        self.assertTrue(freeze["separate_single_owner_activation_required"])

        report["created_at_unix"] = False
        report["report_payload_sha256"] = payload_sha256(
            {key: value for key, value in report.items() if key != "report_payload_sha256"}
        )
        with self.assertRaisesRegex(RuntimeError, "envelope"):
            validate_report(
                report,
                expected_settings=settings,
                protocol_path="results/protocol.json",
                protocol_sha256="a" * 64,
            )

    def test_parent_no_go_cannot_build_report(self) -> None:
        settings = self.settings()
        measurement = run_capacity_ladder(FakeClient(), settings=settings)
        with self.assertRaisesRegex(RuntimeError, "authority"):
            build_report(
                measurement,
                protocol={"path": "p", "sha256": "a" * 64},
                parent_package_gate={
                    "path": "s",
                    "sha256": "b" * 64,
                    "status": "complete_package_gate_no_go",
                    "capacity_measurement_allowed": False,
                    "all220_freeze_design_allowed": False,
                    "contents_emitted": False,
                },
                execution_activation={"path": "a", "sha256": "c" * 64},
                shared_api_lease={
                    "owner": "v24217_post_package_gate_neutral_capacity_v1",
                    "purpose": "neutral_capacity_after_v24216_go_for_next_fresh_all220",
                    "owner_purpose_pid_and_lock_holder_exact": True,
                    "contents_emitted": False,
                },
                created_at_unix=1,
                expected_settings=settings,
            )


if __name__ == "__main__":
    unittest.main()
