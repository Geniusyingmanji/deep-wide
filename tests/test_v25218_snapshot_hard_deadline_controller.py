from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent import v25217_single_snapshot_transport as transport  # noqa: E402
from deepwide_agent import v25218_snapshot_hard_deadline_controller as target  # noqa: E402


def body_for(stratum: str) -> bytes:
    return f"body:{stratum}".encode()


def success_fetch(stratum: str):
    body = body_for(stratum)
    receipt = transport._receipt(
        stratum=stratum,
        provider_attempt_count=1,
        outcome="success",
        failure_code=None,
        http_status=200,
        elapsed_seconds=0.01,
        response_bytes=len(body),
        response_sha256=hashlib.sha256(body).hexdigest(),
    )
    return body, receipt


def one_failure_fetch(stratum: str):
    if stratum == target.STRATA[1]:
        return b"", transport._receipt(
            stratum=stratum,
            provider_attempt_count=1,
            outcome="failure",
            failure_code="http_non200",
            http_status=503,
            elapsed_seconds=0.01,
            response_bytes=0,
            response_sha256=None,
        )
    return success_fetch(stratum)


def slow_fetch(stratum: str):
    if stratum == target.STRATA[-1]:
        time.sleep(2)
    return success_fetch(stratum)


def corrupt_binding_fetch(stratum: str):
    body, receipt = success_fetch(stratum)
    if stratum == target.STRATA[0]:
        return body + b"corrupt", receipt
    return body, receipt


def raising_fetch(stratum: str):
    if stratum == target.STRATA[2]:
        raise RuntimeError("private child exception")
    return success_fetch(stratum)


class V25218SnapshotHardDeadlineControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        if "fork" not in __import__("multiprocessing").get_all_start_methods():
            self.skipTest("fork is required by the frozen controller")

    def test_four_successes_return_exact_in_memory_bodies(self) -> None:
        bodies, receipt = target.run_snapshot_batch(
            fetch=success_fetch, hard_deadline_seconds=2.0
        )
        self.assertEqual(
            bodies, {stratum: body_for(stratum) for stratum in target.STRATA}
        )
        self.assertEqual(receipt["terminal_outcome"], "success")
        self.assertIsNone(receipt["failure_code"])
        self.assertEqual(receipt["successful_transport_count"], 4)
        self.assertTrue(all(row["exit_code"] == 0 for row in receipt["children"].values()))
        rendered = json.dumps(receipt, sort_keys=True)
        self.assertNotIn("body:", rendered)

    def test_one_transport_failure_discards_all_bodies_without_retry(self) -> None:
        bodies, receipt = target.run_snapshot_batch(
            fetch=one_failure_fetch, hard_deadline_seconds=2.0
        )
        self.assertEqual(bodies, {})
        self.assertEqual(receipt["failure_code"], "child_transport_failure")
        failed = receipt["children"][target.STRATA[1]]["transport_receipt"]
        self.assertEqual(failed["retry_count"], 0)
        self.assertFalse(receipt["partial_bodies_returned_on_failure"])

    def test_hard_deadline_terminates_slow_child_and_discards_fast_bodies(self) -> None:
        started = time.monotonic()
        bodies, receipt = target.run_snapshot_batch(
            fetch=slow_fetch, hard_deadline_seconds=0.20
        )
        elapsed = time.monotonic() - started
        self.assertEqual(bodies, {})
        self.assertEqual(receipt["failure_code"], "hard_deadline")
        self.assertLess(elapsed, 1.2)
        self.assertEqual(
            receipt["children"][target.STRATA[-1]]["kind"], "hard_deadline"
        )

    def test_worker_exception_is_content_free_and_discards_all_bodies(self) -> None:
        bodies, receipt = target.run_snapshot_batch(
            fetch=raising_fetch, hard_deadline_seconds=2.0
        )
        self.assertEqual(bodies, {})
        self.assertEqual(receipt["failure_code"], "controller_error")
        self.assertNotIn("private child exception", json.dumps(receipt))

    def test_child_body_receipt_mismatch_fails_closed(self) -> None:
        bodies, receipt = target.run_snapshot_batch(
            fetch=corrupt_binding_fetch, hard_deadline_seconds=2.0
        )
        self.assertEqual(bodies, {})
        self.assertEqual(receipt["failure_code"], "controller_error")

    def test_invalid_deadline_fails_before_children(self) -> None:
        for deadline in (0, 0.01, 181, float("nan"), True):
            with self.subTest(deadline=deadline), self.assertRaises(ValueError):
                target.run_snapshot_batch(
                    fetch=success_fetch, hard_deadline_seconds=deadline
                )

    def test_repeated_timeout_does_not_leak_children_or_file_descriptors(self) -> None:
        before_fds = len(os.listdir("/proc/self/fd"))
        for _ in range(2):
            bodies, receipt = target.run_snapshot_batch(
                fetch=slow_fetch, hard_deadline_seconds=0.15
            )
            self.assertEqual(bodies, {})
            self.assertEqual(receipt["failure_code"], "hard_deadline")
        after_fds = len(os.listdir("/proc/self/fd"))
        self.assertLessEqual(after_fds, before_fds + 2)
        children = __import__("multiprocessing").active_children()
        self.assertEqual(children, [])

    def test_resealed_receipt_tamper_fails_closed(self) -> None:
        _bodies, receipt = target.run_snapshot_batch(
            fetch=success_fetch, hard_deadline_seconds=2.0
        )
        for kind in ("partial", "child", "authority", "credit"):
            changed = copy.deepcopy(receipt)
            if kind == "partial":
                changed["partial_bodies_returned_on_failure"] = True
            elif kind == "child":
                changed["children"][target.STRATA[0]]["exit_code"] = 1
            elif kind == "authority":
                changed[
                    "population_freeze_external_forward_or_runtime_compatibility_authorized"
                ] = True
            else:
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            changed.pop("receipt_payload_sha256")
            changed["receipt_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_receipt(changed)


if __name__ == "__main__":
    unittest.main()
