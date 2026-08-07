from __future__ import annotations

import copy
import io
import sys
import unittest
import urllib.error
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import (  # noqa: E402
    design_v24822_bounded_snapshot_transport_population as target,
)
from tests.test_design_v24820_cell_disjoint_worldbank_population import (  # noqa: E402
    fixture,
)


class Response:
    def __init__(self, raw: bytes, status: int = 200) -> None:
        self.raw = raw
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, limit: int) -> bytes:
        return self.raw[:limit]


class Clock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        self.value += 0.01
        return self.value


class V24822TransportPopulationTests(unittest.TestCase):
    def test_timeout_then_success_is_bounded_and_receipted(self) -> None:
        outcomes = [TimeoutError("slow"), Response(b"payload")]
        sleeps = []

        def opener(_request, *, timeout):
            self.assertEqual(timeout, 90)
            value = outcomes.pop(0)
            if isinstance(value, BaseException):
                raise value
            return value

        raw, receipt = target.fetch_bytes_bounded(
            "https://api.worldbank.org/example",
            opener=opener,
            sleeper=sleeps.append,
            monotonic=Clock(),
        )
        self.assertEqual(raw, b"payload")
        self.assertEqual(receipt["attempt_count"], 2)
        self.assertEqual(receipt["attempts"][0]["outcome"], "failure")
        self.assertEqual(receipt["attempts"][1]["outcome"], "success")
        self.assertEqual(sleeps, [0.5])
        self.assertFalse(receipt["url_or_response_content_emitted"])

    def test_nonretryable_http_error_stops_after_one_attempt(self) -> None:
        def opener(_request, *, timeout):
            del timeout
            raise urllib.error.HTTPError(
                "https://api.worldbank.org/example", 404, "missing", {}, None
            )

        with self.assertRaisesRegex(RuntimeError, "exhausted"):
            target.fetch_bytes_bounded(
                "https://api.worldbank.org/example",
                opener=opener,
                sleeper=lambda _value: self.fail("must not sleep"),
                monotonic=Clock(),
            )

    def test_all_timeouts_stop_at_three_attempts(self) -> None:
        calls = []
        sleeps = []

        def opener(_request, *, timeout):
            calls.append(timeout)
            raise TimeoutError("slow")

        with self.assertRaisesRegex(RuntimeError, "exhausted"):
            target.fetch_bytes_bounded(
                "https://api.worldbank.org/example",
                opener=opener,
                sleeper=sleeps.append,
                monotonic=Clock(),
            )
        self.assertEqual(calls, [90, 90, 90])
        self.assertEqual(sleeps, [0.5, 1.0])

    def test_response_size_and_host_are_guarded(self) -> None:
        with self.assertRaisesRegex(ValueError, "URL"):
            target.fetch_bytes_bounded(
                "https://example.org/not-worldbank",
                opener=lambda *_args, **_kwargs: Response(b"x"),
            )
        with self.assertRaisesRegex(ValueError, "size"):
            target.fetch_bytes_bounded(
                "https://api.worldbank.org/example",
                opener=lambda *_args, **_kwargs: Response(b""),
                monotonic=Clock(),
            )

    def test_successor_keeps_population_semantics_exactly(self) -> None:
        self.assertEqual(target.TARGETS, target.parent.TARGETS)
        self.assertEqual(target.TASK_SIZE, target.parent.TASK_SIZE)
        self.assertEqual(target.TASK_COUNT, target.parent.TASK_COUNT)
        self.assertEqual(target.SELECTED_COUNT, target.parent.SELECTED_COUNT)
        self.assertNotEqual(target.PRIVATE, target.parent.PRIVATE)
        self.assertNotEqual(target.OUTPUT, target.parent.OUTPUT)

    def test_build_artifacts_changes_only_successor_metadata(self) -> None:
        countries, snapshots = fixture(128)
        selected, metrics = target.parent.select_population(
            countries, snapshots, set(), set(), set()
        )
        receipts = []
        for index in range(3):
            raw = f"payload-{index}".encode()
            _value, receipt = target.fetch_bytes_bounded(
                "https://api.worldbank.org/example",
                opener=lambda *_args, _raw=raw, **_kwargs: Response(_raw),
                monotonic=Clock(),
            )
            receipts.append(receipt)
        private, public = target.build_artifacts(
            selected,
            transport_receipts=receipts,
            catalog_metadata={
                "response_sha256": "1" * 64,
                "reported_total": 128,
                "eligible_country_count": 128,
            },
            snapshot_metadata=[
                {
                    "indicator": item["indicator"],
                    "year": item["year"],
                    "source_url": "https://api.worldbank.org/example",
                    "response_sha256": f"{index + 2:064x}",
                    "lastupdated": "2026-08-07",
                    "reported_total": 128,
                    "non_null_country_count": 128,
                    "null_country_count": 0,
                }
                for index, item in enumerate(target.TARGETS)
            ],
            historical_manifest={"historical": "4" * 64},
            metrics=metrics,
            created_at=1,
            git_head="5" * 40,
            authorization_audit_sha256="6" * 64,
        )
        self.assertEqual(len(private["groups"]), 32)
        self.assertEqual(public["transport"]["total_attempt_count"], 3)
        successor = public["append_only_transport_successor"]
        self.assertTrue(
            successor[
                "targets_selection_rank_denominator_disjointness_and_privacy_unchanged"
            ]
        )
        self.assertFalse(successor["same_predecessor_publication_retried_or_resumed"])

    def test_predecessor_surfaces_remain_absent(self) -> None:
        self.assertFalse((ROOT / target.parent.PRIVATE).exists())
        self.assertFalse((ROOT / target.parent.OUTPUT).exists())


if __name__ == "__main__":
    unittest.main()
