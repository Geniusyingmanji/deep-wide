from __future__ import annotations

import threading
import unittest
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24194_capacity_ladder import (
    PROBE_EXPECTED_OUTPUT,
    PROBE_INPUT_UTF8_BYTES,
    PROBE_SYSTEM,
    ProbeSettings,
    build_capacity_freeze,
    build_neutral_probe,
    run_capacity_ladder,
    validate_capacity_report,
)


class FakeClient:
    def __init__(self, failure_at: int | None = None) -> None:
        self.failure_at = failure_at
        self.calls = 0
        self.active = 0
        self.maximum_active = 0
        self.lock = threading.Lock()

    def complete(self, system, user, *, max_output_tokens):
        with self.lock:
            self.calls += 1
            call = self.calls
            self.active += 1
            self.maximum_active = max(self.maximum_active, self.active)
        try:
            success = self.failure_at != call
            return SimpleNamespace(
                text=PROBE_EXPECTED_OUTPUT if success else "WRONG",
                attempts=1,
                output_truncated=False,
                input_utf8_bytes=len((system + user).encode("utf-8")),
                request_body_bytes=PROBE_INPUT_UTF8_BYTES + 100,
                max_output_tokens=max_output_tokens,
            )
        finally:
            with self.lock:
                self.active -= 1


class V24194CapacityLadderTests(unittest.TestCase):
    def test_probe_is_exact_and_contains_no_task_identifier(self) -> None:
        value = build_neutral_probe(7)
        self.assertEqual(len(value.encode("utf-8")), PROBE_INPUT_UTF8_BYTES)
        self.assertNotIn("task_", value)
        self.assertNotIn("DeepWide", value)

    def test_all_levels_pass_and_freeze_caps_shards(self) -> None:
        client = FakeClient()
        settings = ProbeSettings(
            levels=(1, 2, 4),
            waves_per_level=2,
            absolute_latency_ceiling_seconds=999,
            baseline_p95_multiplier=999,
            baseline_median_multiplier=999,
            maximum_parallel_shards=4,
            per_shard_model_workers=2,
        )
        report = run_capacity_ladder(client, settings=settings)
        self.assertEqual(report["selected_model_request_concurrency"], 4)
        self.assertEqual(report["selected_parallel_full220_shards"], 2)
        self.assertFalse(report["full220_launch_allowed"])
        self.assertTrue(
            all(
                not row["output_text_or_response_id_persisted"]
                for level in report["levels"]
                for row in level["requests"]
            )
        )
        freeze = build_capacity_freeze(
            report,
            report_path="results/report.json",
            report_sha256="a" * 64,
            protocol_path="results/protocol.json",
            protocol_sha256="b" * 64,
        )
        self.assertEqual(freeze["parallel_shard_cap"], 2)
        self.assertEqual(freeze["worst_case_model_request_concurrency"], 4)
        self.assertFalse(freeze["full220_launch_allowed"])

    def test_first_unsafe_level_stops_ladder(self) -> None:
        # Level 1 consumes two requests.  The first request at level 2 fails.
        client = FakeClient(failure_at=3)
        settings = ProbeSettings(
            levels=(1, 2, 4),
            waves_per_level=2,
            absolute_latency_ceiling_seconds=999,
            baseline_p95_multiplier=999,
            baseline_median_multiplier=999,
        )
        report = run_capacity_ladder(client, settings=settings)
        self.assertEqual(report["selected_model_request_concurrency"], 1)
        self.assertEqual([row["concurrency"] for row in report["levels"]], [1, 2])
        self.assertFalse(report["levels"][-1]["passed"])
        self.assertEqual(client.calls, 6)

    def test_retry_or_truncation_is_not_a_success(self) -> None:
        class RetryClient(FakeClient):
            def complete(self, *args, **kwargs):
                result = super().complete(*args, **kwargs)
                result.attempts = 2
                return result

        report = run_capacity_ladder(
            RetryClient(),
            settings=ProbeSettings(levels=(1,), waves_per_level=2),
        )
        self.assertEqual(report["selected_model_request_concurrency"], 0)
        self.assertEqual(
            report["levels"][0]["requests"][0]["error_type"],
            "retry_or_truncation_observed",
        )

    def test_serial_only_capacity_produces_one_worker_freeze(self) -> None:
        report = run_capacity_ladder(
            FakeClient(failure_at=3),
            settings=ProbeSettings(
                levels=(1, 2),
                waves_per_level=2,
                absolute_latency_ceiling_seconds=999,
                baseline_p95_multiplier=999,
                baseline_median_multiplier=999,
            ),
        )
        self.assertEqual(report["selected_model_request_concurrency"], 1)
        self.assertEqual(report["selected_per_shard_model_workers"], 1)
        self.assertEqual(report["selected_parallel_full220_shards"], 1)
        freeze = build_capacity_freeze(
            report,
            report_path="results/report.json",
            report_sha256="a" * 64,
            protocol_path="results/protocol.json",
            protocol_sha256="b" * 64,
        )
        self.assertEqual(freeze["worst_case_model_request_concurrency"], 1)

    def test_invalid_level_sequence_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid"):
            ProbeSettings(levels=(2, 1)).validate()

    def test_report_rejects_malformed_numeric_metadata_without_type_error(self) -> None:
        report = run_capacity_ladder(
            FakeClient(),
            settings=ProbeSettings(levels=(1,), waves_per_level=2),
        )
        report["levels"][0]["requests"][0]["elapsed_seconds"] = None
        with self.assertRaisesRegex(RuntimeError, "request metadata"):
            validate_capacity_report(report)

    def test_report_rejects_summary_tampering_even_if_resealed_later(self) -> None:
        report = run_capacity_ladder(
            FakeClient(),
            settings=ProbeSettings(levels=(1,), waves_per_level=2),
        )
        report["selected_model_request_concurrency"] = 0
        with self.assertRaisesRegex(RuntimeError, "summary"):
            validate_capacity_report(report)

    def test_report_rejects_request_success_tampering(self) -> None:
        report = run_capacity_ladder(
            FakeClient(),
            settings=ProbeSettings(levels=(1,), waves_per_level=2),
        )
        report["levels"][0]["requests"][0]["success"] = False
        report["levels"][0]["all_requests_first_attempt_exact_success"] = False
        report["levels"][0]["passed"] = False
        report["selected_model_request_concurrency"] = 0
        report["selected_per_shard_model_workers"] = 0
        report["selected_parallel_full220_shards"] = 0
        report["worst_case_model_request_concurrency"] = 0
        report["status"] = "capacity_no_go_serial_probe_failed"
        with self.assertRaisesRegex(RuntimeError, "success bit"):
            validate_capacity_report(report)


if __name__ == "__main__":
    unittest.main()
