from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import v24752_host_local_gate as target  # noqa: E402


class FakeClock:
    def __init__(self) -> None:
        self.value = 100.0

    def monotonic(self) -> float:
        return self.value

    def sleep(self, duration: float) -> None:
        self.value += duration

    def advance(self, duration: float) -> None:
        self.value += duration


def fake_request(clock: FakeClock):
    def run(index_url: tuple[int, str]):
        index, url = index_url
        clock.advance(0.05)
        return (
            {
                "request_index": index,
                "source_host": target.urlsplit(url).hostname,
            },
            b"x",
        )

    return run


class V24752HostLocalGateTests(unittest.TestCase):
    def test_successor_bindings_are_fresh_and_policy_sealed(self) -> None:
        value = target.successor_bindings()
        self.assertTrue(value["parent_diagnosis_seal_valid"])
        self.assertFalse(value["same_population_retry_authorized"])
        self.assertTrue(value["fresh_scheduler_design_authorized"])
        self.assertTrue(value["population_seal_valid"])
        self.assertTrue(value["policy_seal_valid"])
        self.assertTrue(value["fresh_url_vector_disjoint_from_v24748"])
        self.assertEqual(value["task_count"], 6)
        self.assertEqual(value["request_count"], 32)
        self.assertEqual(target.base.WORKERS, 17)
        self.assertEqual(target._derived_network_wave_ceiling_seconds(), 33.0)

    def test_crossref_lane_is_serial_and_start_paced(self) -> None:
        clock = FakeClock()
        rows = [
            row
            for row in enumerate(target.base._request_vector(), 1)
            if target.urlsplit(row[1]).hostname == target.runtime.CROSSREF_HOST
        ][:3]
        tracker = target._InflightTracker()
        output = target._crossref_lane(
            rows,
            origin=clock.monotonic(),
            tracker=tracker,
            request_one=fake_request(clock),
            monotonic=clock.monotonic,
            sleep=clock.sleep,
        )
        starts = [row[2]["started_offset_seconds"] for row in output]
        self.assertEqual(len(output), 3)
        self.assertEqual(tracker.maximum[target.runtime.CROSSREF_HOST], 1)
        self.assertTrue(
            all(
                starts[index] - starts[index - 1] >= 1.1
                for index in range(1, len(starts))
            )
        )

    def test_schedule_receipt_recomputes_and_tamper_fails(self) -> None:
        clock = FakeClock()
        tracker = target._InflightTracker()
        events = []
        for index, url in enumerate(target.base._request_vector(), 1):
            host = target.urlsplit(url).hostname
            started = clock.monotonic()
            started_sequence = tracker.enter(host)
            clock.advance(0.01)
            completed_sequence = tracker.leave(host)
            events.append(
                {
                    "request_index": index,
                    "source_host": host,
                    "started_offset_seconds": round(started - 100.0, 9),
                    "completed_offset_seconds": round(
                        clock.monotonic() - 100.0, 9
                    ),
                    "started_sequence": started_sequence,
                    "completed_sequence": completed_sequence,
                }
            )
            if host == target.runtime.CROSSREF_HOST:
                clock.advance(1.1)
        # Rebuild Crossref starts to exact policy spacing from their own order.
        next_start = 0.0
        for event in events:
            if event["source_host"] == target.runtime.CROSSREF_HOST:
                event["started_offset_seconds"] = round(next_start, 9)
                event["completed_offset_seconds"] = round(next_start + 0.01, 9)
                next_start += 1.1
        receipt = target._schedule_receipt(events, tracker=tracker)
        self.assertEqual(target.validate_schedule_receipt(receipt), receipt)
        # Exact lifecycle order, not rounded timestamps, proves concurrency.
        collision = [
            {
                "source_host": target.runtime.ROR_HOST,
                "started_offset_seconds": 0.0,
                "completed_offset_seconds": 0.0,
                "started_sequence": 1,
                "completed_sequence": 4,
            },
            {
                "source_host": target.runtime.ROR_HOST,
                "started_offset_seconds": 0.0,
                "completed_offset_seconds": 0.0,
                "started_sequence": 2,
                "completed_sequence": 3,
            },
        ]
        self.assertEqual(
            target._observed_max_inflight(collision, target.runtime.ROR_HOST), 2
        )
        altered = copy.deepcopy(receipt)
        altered["events"][1]["started_offset_seconds"] = 0.0
        altered.pop("schedule_payload_sha256")
        altered["schedule_payload_sha256"] = target.base.payload_sha256(altered)
        with self.assertRaises(RuntimeError):
            target.validate_schedule_receipt(altered)

    def test_protocol_adds_exact_scheduler_binding(self) -> None:
        with (
            patch.object(target.base, "_manifest", return_value={"x": "a" * 64}),
            patch.object(target.base, "_watchers", return_value=[]),
            patch.object(target.base, "sha256", return_value="b" * 64),
            patch.object(target, "_policy", return_value={}),
            patch.object(target.base, "_population", return_value={}),
        ):
            value = target.build_protocol(ROOT, now=0)
        scheduler = value["host_local_scheduler"]
        self.assertEqual(
            scheduler["host_max_inflight"][target.runtime.CROSSREF_HOST], 1
        )
        self.assertEqual(
            scheduler["host_minimum_start_interval_seconds"][
                target.runtime.CROSSREF_HOST
            ],
            1.1,
        )
        self.assertTrue(scheduler["one_attempt_per_url"])
        self.assertEqual(
            scheduler["host_hard_wall_seconds"],
            target.HOST_HARD_WALL_SECONDS,
        )
        self.assertEqual(
            scheduler["derived_network_wave_ceiling_seconds"], 33.0
        )

    def test_request_uses_host_local_hard_wall(self) -> None:
        vectors = {}

        def fake_get(url: str, *, timeout_seconds: float):
            vectors[target.urlsplit(url).hostname] = timeout_seconds
            return {
                "kind": "transport_error",
                "status_code": None,
                "final_url": "",
                "body": b"",
                "elapsed_seconds": 0.0,
            }

        first_by_host = {}
        for index, url in enumerate(target.base._request_vector(), 1):
            first_by_host.setdefault(target.urlsplit(url).hostname, (index, url))
        with patch.object(target.base, "hard_get", side_effect=fake_get):
            for row in first_by_host.values():
                receipt, body = target._host_local_request_one(row)
                self.assertFalse(receipt["transport_success"])
                self.assertEqual(body, b"")
        self.assertEqual(vectors, target.HOST_HARD_WALL_SECONDS)

    def test_result_requires_bound_schedule_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            schedule_path = root / "schedule.json"
            schedule_path.write_text("{}")
            with (
                patch.object(target, "ROOT", root),
                patch.object(target.base, "OUTPUT_ROOT", Path(".")),
                patch.object(target, "SCHEDULE_RECEIPT_NAME", "schedule.json"),
            ):
                value = {"schedule_receipt_sha256": "0" * 64}
                with self.assertRaises(RuntimeError):
                    target.validate_result(value)

    def test_policy_and_population_are_not_forward_private_surfaces(self) -> None:
        self.assertNotIn(
            Path("evaluation/v24750_host_local_population_private_v1_20260806.json"),
            target.base.CONTROL_SURFACE,
        )
        self.assertIn(target.POLICY, target.base.CONTROL_SURFACE)
        self.assertIn(target.POPULATION, target.base.CONTROL_SURFACE)
        self.assertIn(target.PARENT_DIAGNOSIS, target.base.CONTROL_SURFACE)

    def test_ast_label_blind_and_exact_request_vector(self) -> None:
        self.assertEqual(target.base.ast_findings(ROOT), ([], []))
        self.assertEqual(len(target.base._request_vector()), 32)
        self.assertEqual(len(set(target.base._request_vector())), 32)
        self.assertTrue(
            set(target.base._request_vector()).isdisjoint(
                target.helper.PRIOR_ALLOWED_URLS
            )
        )


if __name__ == "__main__":
    unittest.main()
