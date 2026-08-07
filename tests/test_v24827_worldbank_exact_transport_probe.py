from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24826_worldbank_exact_api_transport import (  # noqa: E402
    payload_sha256,
)
from scripts import v24827_worldbank_exact_transport_probe as target  # noqa: E402


def helper_value(*, status: str = "ok", url: str = target.PROBE_URL) -> dict:
    raw = b'[{"page":1},{"country":{"id":"WLD"},"value":1}]'
    success = status == "ok"
    attempt = {
        "attempt": 1,
        "outcome": "success" if success else "failure",
        "http_status": 200 if success else 503,
        "error_type": None if success else "http_503",
        "retryable": False if success else True,
        "elapsed_seconds": 0.1,
        "response_bytes": len(raw) if success else 0,
        "response_sha256": hashlib.sha256(raw).hexdigest() if success else None,
    }
    value = {
        "artifact_version": 1,
        "role": "v24826_worldbank_exact_fetch_result",
        "status": status,
        "url": url,
        "raw_content": raw.decode() if success else "",
        "attempt_count": 1,
        "attempts": [attempt],
        "elapsed_seconds": 0.1,
        "response_bytes": len(raw) if success else 0,
        "response_sha256": hashlib.sha256(raw).hexdigest() if success else None,
    }
    value["result_payload_sha256"] = payload_sha256(value)
    return value


class Process:
    pid = 99_999_999

    def __init__(self, value: dict | None = None, *, timeout: bool = False):
        self.value = value or helper_value()
        self.timeout = timeout
        self.returncode = 0

    def communicate(self, request: str, timeout: float):
        del request, timeout
        if self.timeout:
            raise subprocess.TimeoutExpired("probe", 1)
        return json.dumps(self.value), ""

    def wait(self, timeout: float | None = None):
        del timeout
        self.returncode = -15
        return self.returncode


def successful_receipt(wave: int) -> dict:
    return {
        "wave": wave,
        "helper_status": "ok",
        "terminal_success": True,
        "attempt_count": 1,
        "provider_retry_count": 0,
        "elapsed_seconds": 0.2,
        "response_bytes": 50,
        "http_status_counts": {"200": 1},
        "failure_class_counts": {},
        "response_content_value_or_hash_persisted": False,
    }


class V24827WorldBankExactTransportProbeTests(unittest.TestCase):
    def test_protocol_freezes_nonbenchmark_wld_target_before_outcome(self) -> None:
        with (
            patch.object(target, "_parent_valid", return_value=True),
            patch.object(target, "_manifest", return_value={"x": "a" * 64}),
            patch.object(target, "_watchers", return_value=[]),
            patch.object(target, "sha256", return_value="b" * 64),
        ):
            value = target.build_protocol(ROOT, now=0)
        self.assertEqual(value["target"]["target_key"], target.PROBE_TARGET_KEY)
        self.assertFalse(value["target"]["benchmark_task_or_country_row"])
        self.assertEqual(value["execution"]["requests"], 2)
        self.assertFalse(value["authorization"]["probe_launch"])

    def test_protocol_resealed_target_or_budget_tamper_fails_closed(self) -> None:
        with (
            patch.object(target, "_parent_valid", return_value=True),
            patch.object(target, "_manifest", return_value={"x": "a" * 64}),
            patch.object(target, "_watchers", return_value=[]),
            patch.object(target, "sha256", return_value="b" * 64),
        ):
            value = target.build_protocol(ROOT, now=0)
            value["execution"]["waves"] = 3
            value.pop("protocol_payload_sha256")
            value["protocol_payload_sha256"] = payload_sha256(value)
            with self.assertRaises(RuntimeError):
                target.validate_protocol(ROOT, value=value)

    def test_probe_discards_body_url_and_hash_from_receipt(self) -> None:
        clock = iter((0.0, 0.2))
        receipt = target.run_probe_once(
            1,
            popen=lambda *_args, **_kwargs: Process(),
            monotonic=lambda: next(clock),
        )
        self.assertEqual(set(receipt), target.RECEIPT_KEYS)
        self.assertTrue(receipt["terminal_success"])
        serialized = json.dumps(receipt, sort_keys=True)
        self.assertNotIn("raw_content", serialized)
        self.assertNotIn("response_sha256", serialized)
        self.assertNotIn(target.PROBE_URL, serialized)

    def test_probe_timeout_is_terminal_and_content_free(self) -> None:
        clock = iter((0.0, 50.0))
        with patch.object(target, "_terminate", side_effect=lambda process: process.wait()):
            receipt = target.run_probe_once(
                1,
                popen=lambda *_args, **_kwargs: Process(timeout=True),
                monotonic=lambda: next(clock),
            )
        self.assertEqual(receipt["helper_status"], "hard_total_wall_timeout")
        self.assertFalse(receipt["terminal_success"])
        self.assertEqual(receipt["response_bytes"], 0)

    def test_result_gate_go_and_failure_as_no_go(self) -> None:
        receipts = [successful_receipt(1), successful_receipt(2)]
        with patch.object(target, "sha256", return_value="a" * 64):
            value = target.build_result(
                receipts,
                0.4,
                execution_start_sha256="b" * 64,
                now=0,
            )
        self.assertEqual(value["status"], "transport_probe_go")
        self.assertTrue(value["authorization"]["accounting_successor_design"])
        failed = copy.deepcopy(receipts)
        failed[1] = target._empty_receipt(2, "helper_invalid_result", 0.2)
        with patch.object(target, "sha256", return_value="a" * 64):
            value = target.build_result(
                failed,
                0.4,
                execution_start_sha256="b" * 64,
                now=0,
            )
        self.assertEqual(value["status"], "transport_probe_no_go")
        self.assertFalse(value["authorization"]["accounting_successor_design"])

    def test_resealed_result_content_or_count_tamper_fails_closed(self) -> None:
        with patch.object(target, "sha256", return_value="a" * 64):
            value = target.build_result(
                [successful_receipt(1), successful_receipt(2)],
                0.4,
                execution_start_sha256="b" * 64,
                now=0,
            )
            tampered = copy.deepcopy(value)
            tampered["terminal_success_count"] = 1
            tampered.pop("result_payload_sha256")
            tampered["result_payload_sha256"] = payload_sha256(tampered)
            with self.assertRaises(RuntimeError):
                target.validate_result(
                    tampered, expected_start_sha256="b" * 64
                )
            content = copy.deepcopy(value)
            content["raw_content"] = "forbidden"
            content.pop("result_payload_sha256")
            content["result_payload_sha256"] = payload_sha256(content)
            with self.assertRaises(RuntimeError):
                target.validate_result(
                    content, expected_start_sha256="b" * 64
                )

    def test_runtime_ast_is_label_blind_and_evaluator_free(self) -> None:
        accesses, imports = target.ast_findings(ROOT)
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
